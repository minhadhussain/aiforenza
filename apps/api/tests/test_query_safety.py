"""Exercise the actual HTTP/JSON boundary rather than blacklisting SQL words."""

import asyncio
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.api.routes import chat
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.repositories import api_keys, models, profiles, supabase_rest, topups, usage
from app.services.chat_completions import build_provider_payload
from test_astra_catalog import catalog_row


@pytest.fixture
def wire(monkeypatch):
    monkeypatch.setattr(settings, "supabase_url", "https://database.example.invalid")
    monkeypatch.setattr(settings, "supabase_service_role_key", "PRIVATE_SERVICE_KEY")
    seen = []
    replies = {"status": 200, "body": [{"id": "fixture"}]}

    def handle(request):
        seen.append(request)
        return httpx.Response(replies["status"], json=replies["body"])

    original = httpx.AsyncClient
    monkeypatch.setattr(supabase_rest.httpx, "AsyncClient", lambda *args, **kwargs: original(*args, transport=httpx.MockTransport(handle), **kwargs))
    return seen, replies


@pytest.mark.parametrize("payload", [
    "victim#ignored",
    "victim&user_id=not.is.null",
    "victim&or=(user_id.neq.owner,id.not.is.null)",
    "victim%26user_id%3Dnot.is.null",
    "victim'); DROP TABLE api_keys; --",
])
def test_key_revocation_cannot_smuggle_query_parameters_or_drop_owner_filter(wire, payload):
    seen, _ = wire
    asyncio.run(api_keys.revoke_api_key_record("owner", payload))
    request = seen[0]
    assert request.method == "PATCH" and request.url.path == "/rest/v1/api_keys"
    assert request.url.fragment == ""
    assert request.url.params.multi_items() == [("id", "eq." + payload), ("user_id", "eq.owner")]
    assert set(json.loads(request.content)) == {"revoked_at"}


def test_touch_and_topup_attachment_use_encoded_id_filters(wire):
    seen, _ = wire
    value = "id#fragment&status=neq.PENDING"
    asyncio.run(api_keys.touch_api_key(value))
    asyncio.run(topups.attach_checkout_session_to_topup(topup_id=value, stripe_checkout_session_id="cs_test_fixture';--", stripe_payment_intent_id=None))
    assert len(seen) == 2
    for request in seen:
        assert request.url.fragment == ""
        assert request.url.params.multi_items() == [("id", "eq." + value)]
    assert json.loads(seen[1].content)["stripe_checkout_session_id"] == "cs_test_fixture';--"


@pytest.mark.parametrize("path", [
    "/rest/v1/api_keys?id=eq.anything",
    "/rest/v1/api_keys#fragment",
    "/rest/v1/api_keys;DROP TABLE wallets",
    "/rest/v1/../profiles",
    "/rest/v1/api_keys%3Fid=not.is.null",
    "https://attacker.example/rest/v1/api_keys",
    "//attacker.example/rest/v1/api_keys",
    "/rest/v1/rpc/complete_topup?target_amount_cents=1",
])
def test_database_paths_never_accept_query_or_sql_fragments(wire, path):
    with pytest.raises(supabase_rest.SupabaseRepositoryError, match="Invalid database endpoint"):
        asyncio.run(supabase_rest.rest_select(path, {"select": "id"}))
    assert not wire[0]


@pytest.mark.parametrize("params", [None, {}, {"select": "id"}, {"id": "not.is.null"}, {"id": "eq."}])
def test_patch_requires_an_explicit_equality_target(wire, params):
    with pytest.raises(supabase_rest.SupabaseRepositoryError, match="explicit record filter"):
        asyncio.run(supabase_rest.execute_rest_mutation("/rest/v1/api_keys", "PATCH", {"revoked_at": "now"}, "return=minimal", params=params))
    assert not wire[0]


def test_rpc_accepts_only_rpc_paths_and_json_arguments(wire):
    payload = "quote'); SELECT pg_sleep(10); -- &target_user_id=other#"
    asyncio.run(supabase_rest.execute_rest_rpc("/rest/v1/rpc/hackathon_status", {"target_user_id": payload}))
    request = wire[0][0]
    assert request.url.path == "/rest/v1/rpc/hackathon_status" and not request.url.query
    assert json.loads(request.content) == {"target_user_id": payload}
    with pytest.raises(supabase_rest.SupabaseRepositoryError):
        asyncio.run(supabase_rest.execute_rest_rpc("/rest/v1/wallets", {}))
    assert len(wire[0]) == 1


def test_usage_values_remain_json_data_not_sql_or_query_text(wire):
    poison = "req_'); DROP TABLE usage_records; --"
    asyncio.run(usage.record_usage_charge(user_id="owner", api_key_id="key", model_id="model", request_id=poison, input_tokens=10, output_tokens=10, cached_input_tokens=0, total_tokens=20, reference_charge_cents=100, customer_charge_cents=60, customer_savings_cents=40, provider_cost_cents=None, provider_cost_reference=poison, status="completed"))
    request = wire[0][0]
    assert request.url.path == "/rest/v1/rpc/record_usage_charge" and not request.url.query
    assert json.loads(request.content)["target_request_id"] == poison
    assert json.loads(request.content)["target_provider_cost_reference"] == poison


def test_names_with_sql_syntax_remain_valid_insert_data(wire):
    name = "O'Reilly; SELECT * FROM wallets --"
    payload = {"user_id": str(uuid4()), "name": name, "key_hash": "hash", "key_prefix": "fixture"}
    asyncio.run(api_keys.insert_api_key(payload))
    request = wire[0][0]
    assert request.method == "POST" and request.url.path == "/rest/v1/api_keys"
    assert not request.url.query and json.loads(request.content) == payload


def test_catalog_lookup_does_not_turn_value_into_another_filter(wire):
    wire[1]["body"] = []
    value = "gpt-5.4&enabled=eq.false#' OR TRUE--"
    assert asyncio.run(models.fetch_model_by_slug(value)) is None
    params = wire[0][0].url.params
    assert params.get_list("slug") == ["eq." + value]
    assert params.get_list("enabled") == ["eq.true"]
    assert wire[0][0].url.fragment == ""


@pytest.mark.parametrize("value", ["owner&or=(id.not.is.null)", "';DROP TABLE profiles;--", "bad-uuid", None])
def test_invalid_profile_id_rejected_before_any_database_io(wire, value):
    with pytest.raises(supabase_rest.SupabaseRepositoryError, match="Invalid account identifier"):
        asyncio.run(profiles.fetch_profile(value))
    assert not wire[0]


@pytest.mark.parametrize("value", ["gpt-5.4' OR 1=1--", "gpt-5.4;SELECT pg_sleep(10)", "gpt-5.4&enabled=eq.false", "gpt-5.4#", "a" * 161])
def test_injected_model_identifier_rejected_before_authorization_or_inference(monkeypatch, value):
    authorize = AsyncMock()
    monkeypatch.setattr(chat, "authorize_api_request", authorize)
    response = TestClient(app).post("/v1/chat/completions", json={"model": value, "messages": [{"role": "user", "content": "hello"}]})
    assert response.status_code == 422
    authorize.assert_not_called()


def test_legitimate_sql_prompt_is_not_blocked_or_rewritten():
    prompt = "Explain parameterizing this query: SELECT * FROM users WHERE name = 'O\"Reilly'; DROP TABLE is SQL syntax."
    request = ChatCompletionRequest(model="gpt-5.4", messages=[{"role": "user", "content": prompt}])
    result = build_provider_payload(request, CatalogModel.model_validate(catalog_row("gpt-5.4")), "req_fixture")
    assert result["messages"][0]["content"] == prompt


@pytest.mark.parametrize("body", [
    {"code": "42601", "message": "PRIVATE SQL syntax", "details": "PRIVATE schema", "hint": "PRIVATE values"},
    {"code": "23505", "message": "PRIVATE constraint values"},
    {"code": "P0001", "message": "team_already_claimed; PRIVATE SQL"},
])
def test_database_error_details_are_not_exposed(wire, body):
    wire[1].update(status=400, body=body)
    with pytest.raises(supabase_rest.SupabaseRepositoryError) as caught:
        asyncio.run(supabase_rest.execute_rest_rpc("/rest/v1/rpc/hackathon_status", {"target_user_id": "fixture"}))
    assert "PRIVATE" not in str(caught.value)
    assert "team_already_claimed" not in str(caught.value)


@pytest.mark.parametrize("code", ["insufficient_balance", "team_already_claimed", "invalid_team_id", "campaign_inactive"])
def test_allowlisted_business_errors_preserve_existing_billing_and_claim_behavior(wire, code):
    wire[1].update(status=400, body={"code": "P0001", "message": code})
    with pytest.raises(supabase_rest.SupabaseRepositoryError, match="^" + code + "$"):
        asyncio.run(supabase_rest.execute_rest_rpc("/rest/v1/rpc/hackathon_status", {}))
