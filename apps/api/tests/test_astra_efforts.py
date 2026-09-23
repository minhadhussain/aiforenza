import json
import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.services import access_control, provider_gateway, usage_records
from app.services.chat_completions import build_provider_payload
from app.services.models import serialize_openai_models
from app.services.responses_compat import from_responses, to_responses, stream_to_chat
from app.services.model_capabilities import uses_responses
from app.services.usage_records import preflight_spending_details
from test_astra_catalog import catalog_row

EFFORTS = ["low", "medium", "high", "xhigh", "max"]
TOOLS = [{"type": "function", "function": {"name": "read_fixture", "description": "Read a fixture", "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}}]


def astra():
    return CatalogModel.model_validate(catalog_row("gpt-6-astra"))


def response_fixture():
    return {"id": "resp_fixture", "created_at": 1, "model": "gpt-6-astra-2026-09-03", "status": "completed", "output": [{"type": "reasoning", "encrypted_content": "PRIVATE_REASONING", "summary": []}, {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "OK"}]}], "usage": {"input_tokens": 10, "output_tokens": 1000, "total_tokens": 1010, "input_tokens_details": {"cached_tokens": 0}, "output_tokens_details": {"reasoning_tokens": 800}}}


def frames(events):
    return "".join("data: " + json.dumps(event) + "\n\n" for event in events).encode()


@pytest.fixture
def flow(monkeypatch):
    model = astra()
    model.input_price_per_million = Decimal("0")
    model.output_price_per_million = Decimal("1000")
    key = {"id": "key", "user_id": "owner", "billing_source": "PAID"}
    monkeypatch.setattr(access_control, "authenticate_api_key", AsyncMock(return_value=key))
    monkeypatch.setattr(access_control, "fetch_profile", AsyncMock(return_value={"id": "owner"}))
    monkeypatch.setattr(access_control, "get_model_by_slug", AsyncMock(return_value=model))
    for name in ("fetch_wallet", "fetch_key_wallet"):
        monkeypatch.setattr(access_control, name, AsyncMock(return_value={"balance_cents": 10000, "available_balance_cents": 10000, "currency": "USD"}))
    for name in ("touch_api_key_last_used", "record_rejection", "release_unconsumed_usage"):
        monkeypatch.setattr(access_control, name, AsyncMock())
    for name in ("check_api_rate_limit", "acquire_concurrency_slot", "release_concurrency_slot"):
        monkeypatch.setattr(access_control, name, Mock())
    reserve = AsyncMock(return_value={"reserved": True})
    monkeypatch.setattr(access_control, "reserve_usage", reserve)
    rpc = AsyncMock(return_value={"wallet_id": "wallet", "balance_after_cents": 9900, "transaction_id": "transaction", "usage_record_id": "usage"})
    monkeypatch.setattr(usage_records, "record_usage_charge_rpc", rpc)
    seen = []
    behavior = {"status": 200}

    def handle(request):
        payload = json.loads(request.content)
        seen.append((request.url.path, payload))
        if behavior.get("timeout"):
            raise httpx.ReadTimeout("PRIVATE_TIMEOUT", request=request)
        if behavior["status"] != 200:
            return httpx.Response(behavior["status"], json={"error": {"param": "reasoning_effort", "code": "unsupported_value", "message": "PRIVATE_PROVIDER_SECRET reasoning_effort not supported"}})
        response = response_fixture()
        if request.url.path.endswith("responses"):
            if payload.get("stream"):
                events = [{"type": "response.created", "response": response}, {"type": "response.reasoning_text.delta", "delta": "PRIVATE_REASONING"}, {"type": "response.output_text.delta", "delta": "OK"}, {"type": "response.completed", "response": response}]
                return httpx.Response(200, content=frames(events), headers={"Content-Type": "text/event-stream"})
            return httpx.Response(200, json=response)
        chat = from_responses(response)
        chat["choices"][0]["message"]["reasoning_content"] = "PRIVATE_REASONING"
        if payload.get("stream"):
            chunk = {"choices": [{"index": 0, "delta": {"content": "OK", "reasoning_content": "PRIVATE_REASONING"}, "finish_reason": "stop"}], "usage": chat["usage"]}
            return httpx.Response(200, content=frames([chunk]) + b"data: [DONE]\n\n", headers={"Content-Type": "text/event-stream"})
        return httpx.Response(200, json=chat)

    original = httpx.AsyncClient
    monkeypatch.setattr(provider_gateway.httpx, "AsyncClient", lambda *args, **kwargs: original(*args, transport=httpx.MockTransport(handle), **kwargs))
    return model, key, reserve, rpc, seen, behavior


def request_body(**extras):
    return {"model": "gpt-6-astra", "messages": [{"role": "user", "content": "PRIVATE_PROMPT"}], "max_tokens": 1200, **extras}


def post(body):
    return TestClient(app).post("/v1/chat/completions", headers={"Authorization": "Bearer PRIVATE_API_KEY"}, json=body)


def test_astra_registry_exact_efforts_and_limits():
    model = astra()
    entry = serialize_openai_models([model])["data"][0]
    assert entry["id"] == "gpt-6-astra"
    assert entry["capabilities"]["reasoning_efforts"] == EFFORTS
    assert entry["capabilities"]["reasoning"] is True
    assert entry["capabilities"]["default_reasoning_effort"] == "medium"
    assert entry["limit"] == {"context": 128000, "output": 32768}


@pytest.mark.parametrize("effort", EFFORTS)
@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("source,charge,reservation", [("PAID", 60, 72), ("PROMOTIONAL", 100, 120)])
def test_effort_reaches_provider_and_actual_usage_bills_without_effort_multiplier(flow, effort, stream, source, charge, reservation, caplog):
    model, key, reserve, rpc, seen, _ = flow
    key["billing_source"] = source
    result = post(request_body(reasoning_effort=effort, stream=stream, temperature=0.5, top_p=0.8, reasoningSummary="auto", arbitrary_secret="PRIVATE_EXTRA"))
    assert result.status_code == 200
    assert "PRIVATE_REASONING" not in result.text
    assert len(seen) == 1
    path, outgoing = seen[0]
    assert outgoing["model"] == model.provider_model_id
    assert (outgoing["reasoning"]["effort"] if path.endswith("responses") else outgoing["reasoning_effort"]) == effort
    assert path.endswith("responses") == (effort == "max")
    assert not any(k in outgoing for k in ("temperature", "top_p", "reasoningSummary", "arbitrary_secret", "max_tokens"))
    assert reserve.call_args.args[-1] == reservation
    assert rpc.call_args.kwargs["output_tokens"] == 1000  # Includes 800 reasoning tokens, once.
    assert rpc.call_args.kwargs["reference_charge_cents"] == 100
    assert rpc.call_args.kwargs["customer_charge_cents"] == charge
    assert rpc.call_args.kwargs["customer_savings_cents"] == 100 - charge
    assert "PRIVATE" not in caplog.text
    assert effort in caplog.text and "provider_response" in caplog.text and "usage_settled" in caplog.text
    if stream:
        assert "data: [DONE]" in result.text


@pytest.mark.parametrize("effort", ["none", "minimal", "invalid", "MAX", 1, {}, []])
def test_bad_effort_clean_400_before_any_hold(flow, effort):
    result = post(request_body(reasoning_effort=effort))
    assert result.status_code == 400 and result.json()["error"]["code"] == "unsupported_reasoning_effort"
    flow[2].assert_not_called()
    flow[3].assert_not_called()
    assert not flow[4]


@pytest.mark.parametrize("option", [{"reasoning_effort": "xhigh"}, {"reasoning": {"effort": "xhigh"}}, {"reasoningEffort": "xhigh"}])
def test_open_code_style_aliases_and_tools_use_same_effort(flow, option):
    result = post(request_body(tools=TOOLS, tool_choice="auto", **option))
    assert result.status_code == 200
    path, payload = flow[4][0]
    assert path.endswith("responses") and payload["reasoning"] == {"effort": "xhigh"}
    assert payload["tools"][0]["name"] == "read_fixture"


def test_default_is_medium_and_conflicting_aliases_rejected(flow):
    assert post(request_body()).status_code == 200
    assert flow[4][0][1]["reasoning_effort"] == "medium"
    result = post(request_body(reasoning_effort="high", reasoning={"effort": "low"}))
    assert result.status_code == 400 and result.json()["error"]["code"] == "conflicting_reasoning_effort"
    assert len(flow[4]) == 1


@pytest.mark.parametrize("status,timeout,released", [(400, False, True), (500, False, False), (200, True, False)])
def test_provider_rejection_never_downgrades_and_retains_safety_policy(flow, status, timeout, released, caplog):
    flow[-1].update(status=status, timeout=timeout)
    result = post(request_body(reasoning_effort="max", stream=True))
    assert result.status_code == (400 if released else 502)
    assert len(flow[4]) == 1 and flow[4][0][1]["reasoning"]["effort"] == "max"
    assert access_control.release_unconsumed_usage.await_count == int(released)
    flow[3].assert_not_called()
    assert "PRIVATE" not in result.text and "PRIVATE" not in caplog.text
    if released:
        assert result.json()["error"]["code"] == "provider_reasoning_unavailable"


@pytest.mark.parametrize("slug", ["gpt-5.4", "gpt-5.6-sol"])
def test_other_models_keep_existing_chat_contract(slug):
    model = CatalogModel.model_validate(catalog_row(slug))
    request = ChatCompletionRequest(**request_body(model=slug, reasoning_effort="none", temperature=0.7, tools=TOOLS))
    payload = build_provider_payload(request, model, "req_test")
    assert payload["reasoning_effort"] == "none" and payload["temperature"] == 0.7
    assert payload["tools"] == TOOLS and payload["max_completion_tokens"] == 1200
    assert serialize_openai_models([model])["data"][0]["capabilities"]["reasoning"] is True


def test_stateless_tool_result_conversation_and_schema_preserved():
    request = ChatCompletionRequest(**request_body(tools=TOOLS, tool_choice={"type": "function", "function": {"name": "read_fixture"}}))
    payload = build_provider_payload(request, astra(), "req_test")
    payload["messages"] += [{"role": "assistant", "content": None, "tool_calls": [{"id": "call_fixture", "type": "function", "function": {"name": "read_fixture", "arguments": '{"path":"fixture.txt"}'}}]}, {"role": "tool", "tool_call_id": "call_fixture", "content": "fixture text"}]
    result = to_responses(payload)
    assert result["input"][-2]["type"] == "function_call"
    assert result["input"][-1] == {"type": "function_call_output", "call_id": "call_fixture", "output": "fixture text"}
    assert result["tools"][0]["parameters"] == TOOLS[0]["function"]["parameters"]
    assert result["tool_choice"] == {"type": "function", "name": "read_fixture"}
    assert result["store"] is False


def test_high_effort_does_not_multiply_reservation(flow):
    estimates = [preflight_spending_details(ChatCompletionRequest(**request_body(reasoning_effort=e)), flow[0]) for e in EFFORTS]
    assert {value["customer_charge_cents"] for value in estimates} == {72}
    assert {value["max_output_tokens"] for value in estimates} == {1200}


@pytest.mark.parametrize("effort,tools,expected", [(None, True, True), ("medium", True, True), ("none", True, False), ("medium", False, False)])
def test_sol_only_bridges_azure_incompatible_tool_combinations(effort, tools, expected):
    model = CatalogModel.model_validate(catalog_row("gpt-5.6-sol"))
    request = ChatCompletionRequest(**request_body(model=model.slug, tools=TOOLS if tools else [], reasoning_effort=effort))
    payload = build_provider_payload(request, model, "req_test")
    assert uses_responses(payload, model) == expected


def test_fragmented_responses_stream_preserves_tool_ids_arguments_and_hides_reasoning():
    final = response_fixture()
    final["output"] = [{"type": "function_call", "call_id": "call_1", "name": "read_fixture", "arguments": '{"path":"café.py"}'}]
    events = [{"type": "response.created", "response": final}, {"type": "response.reasoning_text.delta", "delta": "PRIVATE_THOUGHT"}, {"type": "response.output_item.added", "output_index": 1, "item": {**final["output"][0], "arguments": ""}}, {"type": "response.function_call_arguments.delta", "output_index": 1, "delta": '{"path":'}, {"type": "response.function_call_arguments.delta", "output_index": 1, "delta": '"café.py"}'}, {"type": "response.completed", "response": final}]
    raw = frames(events)

    async def source():
        for start in range(0, len(raw), 7):
            yield raw[start:start + 7]

    async def collect():
        return b"".join([chunk async for chunk in stream_to_chat(source())]).decode()

    text = asyncio.run(collect())
    assert "PRIVATE_THOUGHT" not in text and "data: [DONE]" in text
    payloads = [json.loads(line[6:]) for line in text.splitlines() if line.startswith("data: {")]
    calls = [p["choices"][0]["delta"]["tool_calls"][0] for p in payloads if "tool_calls" in p["choices"][0]["delta"]]
    assert calls[0]["id"] == "call_1" and {c["index"] for c in calls} == {0}
    assert "".join(c["function"].get("arguments", "") for c in calls) == '{"path":"café.py"}'
    assert payloads[-1]["choices"][0]["finish_reason"] == "tool_calls"
    assert payloads[-1]["usage"]["completion_tokens"] == 1000


def test_max_output_incomplete_is_accounted_as_length_not_invented_success():
    response = response_fixture()
    response.update(status="incomplete", incomplete_details={"reason": "max_output_tokens"}, output=[])
    translated = from_responses(response)
    assert translated["choices"][0]["finish_reason"] == "length"
    assert translated["choices"][0]["message"]["content"] is None
    assert translated["usage"]["completion_tokens"] == 1000


def test_diagnostics_do_not_log_unknown_legacy_effort_or_extra_fields(caplog):
    provider_gateway.diagnostic({"model": "gpt-5.4", "request_id": "req_fixture", "reasoning_effort": "PRIVATE_EFFORT", "prompt": "PRIVATE_PROMPT", "api_key": "PRIVATE_KEY"}, "provider_request")
    assert "PRIVATE" not in caplog.text


@pytest.mark.parametrize("slug,effort", [
    (slug, effort)
    for slug, efforts in (("gpt-5.4", ["none", "low", "medium", "high", "xhigh"]), ("gpt-5.6-sol", ["none", "low", "medium", "high", "xhigh", "max"]))
    for effort in efforts
])
@pytest.mark.parametrize("source,charge", [("PAID", 60), ("PROMOTIONAL", 100)])
def test_gpt5_variants_reach_provider_with_actual_usage_billing(flow, slug, effort, source, charge):
    model, key, reserve, rpc, seen, _ = flow
    model.slug = model.provider_model_id = slug
    model.capabilities = CatalogModel.model_validate(catalog_row(slug)).capabilities
    key["billing_source"] = source
    result = post(request_body(model=slug, reasoning_effort=effort, tools=TOOLS, stream=True))
    assert result.status_code == 200 and "data: [DONE]" in result.text
    path, outgoing = seen[0]
    expected_responses = slug == "gpt-5.6-sol" and effort != "none"
    assert path.endswith("responses") == expected_responses
    assert (outgoing["reasoning"]["effort"] if expected_responses else outgoing["reasoning_effort"]) == effort
    assert rpc.call_args.kwargs["customer_charge_cents"] == charge
    assert rpc.call_args.kwargs["output_tokens"] == 1000


@pytest.mark.parametrize("slug,effort", [("gpt-5.4", "max"), ("gpt-5.4", "minimal"), ("gpt-5.6-sol", "minimal")])
def test_gpt5_unsupported_efforts_rejected_before_reservation(flow, slug, effort):
    flow[0].slug = flow[0].provider_model_id = slug
    flow[0].capabilities = CatalogModel.model_validate(catalog_row(slug)).capabilities
    result = post(request_body(model=slug, reasoning_effort=effort))
    assert result.status_code == 400
    flow[2].assert_not_called()


def test_gpt54_legacy_function_and_sampling_fields_are_preserved():
    model = CatalogModel.model_validate(catalog_row("gpt-5.4"))
    request = ChatCompletionRequest(**request_body(model=model.slug, functions=[{"name": "legacy"}], function_call="auto", temperature=0.7, top_p=0.9))
    payload = build_provider_payload(request, model, "req_fixture")
    assert payload["reasoning_effort"] == "none"
    assert payload["functions"] == [{"name": "legacy"}]
    assert payload["function_call"] == "auto"
    assert payload["temperature"] == 0.7 and payload["top_p"] == 0.9
