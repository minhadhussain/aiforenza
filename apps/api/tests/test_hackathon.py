import asyncio
import json
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps.auth import get_current_dashboard_user
from app.api.routes import hackathon, chat
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services import access_control, api_keys, usage_records
from app.services.pricing import calculate_pricing_breakdown
from app.models.usage import UsageMetrics
from test_pricing import build_model


@pytest.fixture
def claimant(monkeypatch):
    app.dependency_overrides[get_current_dashboard_user] = lambda: {
        "id": "owner",
        "email": "test@example.invalid",
    }
    monkeypatch.setattr(
        hackathon, "fetch_profile", AsyncMock(return_value={"id": "owner"})
    )
    monkeypatch.setattr(hackathon, "check_api_rate_limit", Mock())
    rpc = AsyncMock(
        return_value={
            "team_id": "HACK-042",
            "promo_balance_cents": 10000,
            "billing_source": "PROMOTIONAL",
        }
    )
    monkeypatch.setattr(hackathon, "claim_team", rpc)
    yield TestClient(app), rpc
    app.dependency_overrides.clear()


def test_claim_authentication_required():
    assert (
        TestClient(app)
        .post("/v1/hackathon/claim", json={"team_id": "HACK-042"})
        .status_code
        == 401
    )
    assert TestClient(app).get("/v1/hackathon/status").status_code == 401


def test_claim_generates_hash_only_and_secret_once(claimant, monkeypatch):
    client, rpc = claimant
    response = client.post("/v1/hackathon/claim", json={"team_id": "hack-042"})
    assert (
        response.status_code == 201 and response.headers["cache-control"] == "no-store"
    )
    key = response.json()["plaintext_key"]
    assert key.startswith("sk_af_hackathon_") and len(key) > 40
    assert rpc.call_args.args == (
        "owner",
        "HACK-042",
        api_keys.hash_api_key(key),
        api_keys.key_prefix_for(key),
    )
    assert key not in str(rpc.call_args)
    rpc.side_effect = SupabaseRepositoryError("team_already_claimed")
    duplicate = client.post("/v1/hackathon/claim", json={"team_id": "HACK-042"})
    assert (
        duplicate.status_code == 409
        and duplicate.json()["detail"]["code"] == "team_already_claimed"
    )
    assert "plaintext_key" not in duplicate.text and key not in duplicate.text
    monkeypatch.setattr(
        hackathon,
        "grant_status",
        AsyncMock(
            return_value={"campaign": None, "grants": [response.json()["grant"]]}
        ),
    )
    status = client.get("/v1/hackathon/status")
    assert (
        status.status_code == 200
        and "plaintext_key" not in status.text
        and key not in status.text
    )


@pytest.mark.parametrize(
    "code,status",
    [
        ("invalid_team_id", 404),
        ("campaign_inactive", 409),
        ("PRIVATE_DATABASE_CREDENTIAL", 503),
    ],
)
def test_claim_errors_are_deterministic_and_redacted(claimant, code, status):
    client, rpc = claimant
    rpc.side_effect = SupabaseRepositoryError(code)
    response = client.post("/v1/hackathon/claim", json={"team_id": "HACK-999"})
    assert response.status_code == status and "PRIVATE" not in response.text


def test_uncertain_claim_never_reissues_or_exposes_secret(claimant):
    client, rpc = claimant
    rpc.side_effect = httpx.ReadTimeout("PRIVATE upstream details")
    response = client.post("/v1/hackathon/claim", json={"team_id": "HACK-042"})
    assert response.status_code == 503
    assert "Check your grant status" in response.text
    assert "PRIVATE" not in response.text and "plaintext_key" not in response.text
    rpc.assert_awaited_once()


def test_key_generation_preserves_paid_format_and_strong_shared_credentials():
    paid = api_keys.generate_api_key()
    shared = {api_keys.generate_api_key(billing_source="PROMOTIONAL") for _ in range(50)}
    assert paid.startswith("sk_live_") and len(paid.removeprefix("sk_live_")) == 32
    assert len(shared) == 50
    assert all(len(key.removeprefix("sk_af_hackathon_")) == 32 for key in shared)
    with pytest.raises(ValueError):
        api_keys.generate_api_key(billing_source="UNKNOWN")


@pytest.mark.parametrize(
    "body",
    [
        {"team_id": "x"},
        {"team_id": "HACK 042"},
        {"team_id": "HACK-042", "user_id": "other"},
        {"team_id": "HACK-042", "grant_amount_cents": 100000},
    ],
)
def test_claim_does_not_trust_client_scope_or_amount(claimant, body):
    client, rpc = claimant
    assert client.post("/v1/hackathon/claim", json=body).status_code == 422
    rpc.assert_not_called()


def test_reference_pricing_no_discount_cached_usage_and_provider_cost():
    model = build_model()
    model.input_price_per_million = Decimal("1000")
    model.output_price_per_million = Decimal("2000")
    model.cached_input_price_per_million = Decimal("100")
    usage = UsageMetrics(input_tokens=1000, output_tokens=100, cached_input_tokens=200)
    paid = calculate_pricing_breakdown(model, usage, provider_cost_cents=4)
    promo = calculate_pricing_breakdown(
        model, usage, provider_cost_cents=4, billing_source="PROMOTIONAL"
    )
    assert promo.reference_charge_cents == promo.customer_charge_cents == 102
    assert paid.customer_charge_cents == 62 and paid.customer_savings_cents == 40
    assert (
        promo.customer_savings_cents == 0
        and promo.provider_cost_cents == paid.provider_cost_cents == 4
    )
    with pytest.raises(ValueError):
        calculate_pricing_breakdown(model, usage, billing_source="FAKE")


@pytest.fixture
def billing(monkeypatch):
    model = build_model()
    model.input_price_per_million = Decimal("0")
    model.output_price_per_million = Decimal("1000")
    key = {
        "id": "key",
        "user_id": "owner",
        "billing_source": "PROMOTIONAL",
        "hackathon_grant_id": "grant",
    }
    monkeypatch.setattr(
        access_control, "authenticate_api_key", AsyncMock(return_value=key)
    )
    monkeypatch.setattr(
        access_control, "fetch_profile", AsyncMock(return_value={"id": "owner"})
    )
    personal = AsyncMock(
        return_value={
            "balance_cents": 100000,
            "available_balance_cents": 100000,
            "currency": "USD",
        }
    )
    promo = {
        "balance_cents": 10000,
        "available_balance_cents": 10000,
        "currency": "USD",
        "billing_source": "PROMOTIONAL",
    }
    monkeypatch.setattr(access_control, "fetch_wallet", personal)
    monkeypatch.setattr(
        access_control, "fetch_key_wallet", AsyncMock(return_value=promo)
    )
    monkeypatch.setattr(
        access_control, "get_model_by_slug", AsyncMock(return_value=model)
    )
    monkeypatch.setattr(access_control, "touch_api_key_last_used", AsyncMock())
    monkeypatch.setattr(access_control, "record_rejection", AsyncMock())
    for name in (
        "check_api_rate_limit",
        "acquire_concurrency_slot",
        "release_concurrency_slot",
    ):
        monkeypatch.setattr(access_control, name, Mock())
    reservation = AsyncMock(return_value={"reserved": True})
    monkeypatch.setattr(access_control, "reserve_usage", reservation)
    rpc = AsyncMock(
        return_value={
            "wallet_id": "wallet",
            "balance_after_cents": 9900,
            "transaction_id": "transaction",
            "usage_record_id": "usage",
        }
    )
    monkeypatch.setattr(usage_records, "record_usage_charge_rpc", rpc)
    response = {
        "choices": [{"message": {"content": "OK"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 1000, "total_tokens": 1010},
    }
    provider = AsyncMock(return_value=response)
    monkeypatch.setattr(chat, "forward_chat_completion", provider)
    return key, promo, personal, reservation, rpc, provider, response


def test_promo_key_reserves_and_settles_reference_not_personal_wallet(billing):
    key, promo, personal, reserve, rpc, _, _ = billing
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer shared-key"},
        json={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1000,
        },
    )
    assert response.status_code == 200
    assert reserve.call_args.args[-1] == 100
    assert (
        rpc.call_args.kwargs["customer_charge_cents"]
        == rpc.call_args.kwargs["reference_charge_cents"]
        == 100
    )
    assert rpc.call_args.kwargs["customer_savings_cents"] == 0
    personal.assert_not_called()


def test_personal_key_keeps_discount_and_ignores_request_source(billing):
    key, promo, personal, reserve, rpc, _, _ = billing
    key["billing_source"] = "PAID"
    key["hackathon_grant_id"] = None
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer shared-key"},
        json={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1000,
            "billing_source": "PROMOTIONAL",
        },
    )
    assert response.status_code == 200 and reserve.call_args.args[-1] == 60
    assert rpc.call_args.kwargs["customer_charge_cents"] == 60
    personal.assert_awaited_once()
    access_control.fetch_key_wallet.assert_not_called()


def test_exhausted_promo_returns_402_without_paid_fallback(billing):
    _, promo, personal, reserve, rpc, provider, _ = billing
    promo.update(balance_cents=0, available_balance_cents=0)
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer shared-key"},
        json={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1000,
        },
    )
    assert response.status_code == 402
    personal.assert_not_called()
    reserve.assert_not_called()
    provider.assert_not_called()
    rpc.assert_not_called()


@pytest.mark.parametrize("definitive", [True, False])
def test_promo_provider_release_policy_unchanged(billing, monkeypatch, definitive):
    from app.core.errors import OpenAIAPIError

    *_, provider, response = billing
    req = httpx.Request("POST", "https://fixture.invalid")
    cause = (
        httpx.HTTPStatusError(
            "rejected", request=req, response=httpx.Response(400, request=req)
        )
        if definitive
        else httpx.ReadTimeout("uncertain", request=req)
    )
    failure = OpenAIAPIError(
        "Provider unavailable",
        error_type="api_error",
        code="provider_unavailable",
        status_code=502,
    )
    failure.__cause__ = cause
    provider.side_effect = failure
    release = AsyncMock()
    monkeypatch.setattr(access_control, "release_unconsumed_usage", release)
    result = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer shared-key"},
        json={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1000,
        },
    )
    assert result.status_code == 502 and release.await_count == int(definitive)


def test_promotional_stream_settles_before_done(billing, monkeypatch):
    *_, response = billing

    async def source():
        yield ("data: " + json.dumps(response) + "\n\n").encode()
        yield b"data: [DONE]\n\n"

    monkeypatch.setattr(
        chat, "forward_chat_completion_stream", AsyncMock(return_value=source())
    )
    result = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer shared-key"},
        json={
            "model": "gpt-5.4",
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 1000,
            "stream": True,
        },
    )
    assert result.status_code == 200 and "data: [DONE]" in result.text
    assert billing[4].call_args.kwargs["customer_charge_cents"] == 100


@pytest.mark.parametrize("active", [True, False])
def test_shared_key_uses_central_auth_and_grant_status(monkeypatch, active):
    from app.repositories import hackathon as repo

    monkeypatch.setattr(
        api_keys,
        "fetch_api_key_by_hash",
        AsyncMock(
            return_value={
                "id": "key",
                "user_id": "owner",
                "billing_source": "PROMOTIONAL",
                "hackathon_grant_id": "grant",
            }
        ),
    )
    monkeypatch.setattr(
        repo,
        "fetch_active_key_grant",
        AsyncMock(return_value={"id": "grant"} if active else None),
    )
    result = asyncio.run(api_keys.authenticate_api_key("shared-secret"))
    assert bool(result) == active


def test_models_endpoint_accepts_shared_key_without_dashboard_login(monkeypatch):
    from app.api.routes import models
    from app.repositories import hackathon as repo

    monkeypatch.setattr(api_keys, "fetch_api_key_by_hash", AsyncMock(return_value={
        "id": "shared", "user_id": "owner", "billing_source": "PROMOTIONAL",
        "hackathon_grant_id": "grant",
    }))
    monkeypatch.setattr(repo, "fetch_active_key_grant", AsyncMock(return_value={"id": "grant"}))
    monkeypatch.setattr(api_keys, "touch_api_key", AsyncMock())
    monkeypatch.setattr(models, "list_models", AsyncMock(return_value=[build_model()]))
    response = TestClient(app).get("/v1/models", headers={"Authorization": "Bearer shared-secret"})
    assert response.status_code == 200 and response.json()["data"][0]["id"] == build_model().slug
    api_keys.fetch_api_key_by_hash.assert_awaited_once_with(api_keys.hash_api_key("shared-secret"))
