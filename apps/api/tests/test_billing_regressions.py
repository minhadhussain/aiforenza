import asyncio
import json
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError
from redis.exceptions import ConnectionError as RedisConnectionError

from app.core.errors import OpenAIAPIError
from app.models.openai import ChatCompletionRequest
from app.models.usage import UsageMetrics
from app.services import api_keys, rate_limit, usage_records
from app.services.chat_completions import build_provider_payload
from app.services.pricing import calculate_pricing_breakdown
from test_pricing import build_model


def test_cached_tokens_are_not_double_charged():
    result = calculate_pricing_breakdown(build_model(), UsageMetrics(input_tokens=1000000, output_tokens=0, cached_input_tokens=1000000))
    assert (result.reference_charge_cents, result.customer_charge_cents, result.customer_savings_cents) == (500, 300, 200)


def test_positive_price_small_request_never_rounds_to_free():
    result = calculate_pricing_breakdown(build_model(), UsageMetrics(input_tokens=1, output_tokens=1))
    assert result.customer_charge_cents == 1
    assert result.reference_charge_cents - result.customer_charge_cents == result.customer_savings_cents


@pytest.mark.parametrize("usage", [{"input_tokens": -1, "output_tokens": 0}, {"input_tokens": 1, "output_tokens": 0, "cached_input_tokens": 2}, {"input_tokens": 1.5, "output_tokens": 0}])
def test_invalid_usage_rejected(usage):
    with pytest.raises(ValidationError):
        UsageMetrics(**usage)


def test_missing_usage_never_invented():
    with pytest.raises(OpenAIAPIError, match="usage"):
        usage_records.extract_usage_metrics({"choices": []}, ChatCompletionRequest(model="test", messages=[{"role": "user", "content": "Hello"}]))


def test_tool_call_messages_and_output_budget_preserved():
    request = ChatCompletionRequest(model="test", stream=True, messages=[{
        "role": "assistant", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "lookup", "arguments": "{}"}}]
    }, {"role": "tool", "tool_call_id": "call_1", "content": "done"}])
    payload = build_provider_payload(request, build_model(), "req_test")
    assert payload["messages"][0]["tool_calls"][0]["id"] == "call_1"
    assert payload["messages"][1]["tool_call_id"] == "call_1"
    assert payload["max_completion_tokens"] == 1024
    assert payload["stream_options"] == {"include_usage": True}


def test_fragmented_stream_bills_before_done(monkeypatch):
    billed = []
    async def charge(**kwargs):
        billed.append(kwargs)
    monkeypatch.setattr(usage_records, "record_usage_charge", charge)
    async def run():
        raw = ('data: ' + json.dumps({"choices": [{"delta": {"content": "héllo"}}]}) + '\r\n\r\n' +
               'data: ' + json.dumps({"choices": [], "usage": {"prompt_tokens": 20, "completion_tokens": 5, "prompt_tokens_details": {"cached_tokens": 3}}}) + '\n\ndata: [DONE]\n\n').encode()
        async def source():
            for byte in raw:
                yield bytes([byte])
        output = []
        async for chunk in usage_records.stream_and_charge(source=source(), request=ChatCompletionRequest(model="test", messages=[{"role":"user","content":"Hello"}]), model=build_model(), user_id="u", api_key_id="k", request_id="r"):
            if b"[DONE]" in chunk:
                assert len(billed) == 1
            output.append(chunk)
        assert b"[DONE]" in b"".join(output)
    asyncio.run(run())
    assert billed[0]["usage"] == UsageMetrics(input_tokens=20, output_tokens=5, cached_input_tokens=3)


def test_billing_total_excludes_cached_subset(monkeypatch):
    rpc = AsyncMock(return_value={"wallet_id":"w","balance_after_cents":400,"transaction_id":"t","usage_record_id":"u"})
    monkeypatch.setattr(usage_records, "record_usage_charge_rpc", rpc)
    asyncio.run(usage_records.record_usage_charge(user_id="u", api_key_id="k", model=build_model(), request_id="r", usage=UsageMetrics(input_tokens=20,output_tokens=5,cached_input_tokens=3), provider_cost_reference="ref", status="completed"))
    assert rpc.call_args.kwargs["total_tokens"] == 25


@pytest.mark.parametrize("operation", [rate_limit.check_api_rate_limit, rate_limit.acquire_concurrency_slot])
def test_redis_outage_fails_closed(monkeypatch, operation):
    class BrokenRedis:
        def eval(self, *args):
            raise RedisConnectionError("private internal address")
    monkeypatch.setattr(rate_limit, "_client", lambda: BrokenRedis())
    with pytest.raises(OpenAIAPIError) as error:
        operation(user_id="u", api_key_id="k")
    assert error.value.status_code == 503
    assert "private" not in str(error.value)


@pytest.mark.parametrize("operation,code", [(rate_limit.check_api_rate_limit,"rate_limit_exceeded"),(rate_limit.acquire_concurrency_slot,"concurrency_limit_exceeded")])
def test_limits_reject_when_atomic_script_denies(monkeypatch, operation, code):
    class LimitedRedis:
        def eval(self, *args):
            return 0
    monkeypatch.setattr(rate_limit, "_client", lambda: LimitedRedis())
    with pytest.raises(OpenAIAPIError) as error:
        operation(user_id="u", api_key_id="k")
    assert error.value.code == code
    assert error.value.status_code == 429


def test_generated_key_is_hashed_and_revocation_rejected(monkeypatch):
    stored = {}
    async def insert(payload):
        stored.update(payload)
        return {"id":"key", **payload}
    async def lookup(value):
        return stored if value == stored.get("key_hash") else None
    monkeypatch.setattr(api_keys,"insert_api_key",insert)
    monkeypatch.setattr(api_keys,"fetch_api_key_by_hash",lookup)
    result = asyncio.run(api_keys.create_api_key_record("user","test"))
    key = result["plaintext_key"]
    assert key not in str(stored)
    assert asyncio.run(api_keys.authenticate_api_key(key)) is not None
    stored["revoked_at"] = "2026-01-01"
    assert asyncio.run(api_keys.authenticate_api_key(key)) is None
    assert asyncio.run(api_keys.authenticate_api_key("invalid")) is None
