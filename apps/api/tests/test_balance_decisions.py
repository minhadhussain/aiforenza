import asyncio
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import chat
from app.services import access_control
from app.services.usage_records import preflight_spending_details
from app.services.pricing import calculate_pricing_breakdown
from app.models.openai import ChatCompletionRequest
from app.models.usage import UsageMetrics
from app.repositories.wallets import build_wallet_summary
from test_pricing import build_model


def request_payload(normal=False):
    return {
        "model": "gpt-5.4",
        "messages": [
            {"role": "system", "content": "Use the tools to answer questions."},
            {"role": "user", "content": "Say OK"},
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file",
                    "parameters": {
                        "type": "object",
                        "properties": {"path": {"type": "string"}},
                    },
                },
            }
        ]
        if normal
        else [],
        "max_tokens": 32000 if normal else 16,
        "stream": False,
    }


@pytest.fixture
def setup(monkeypatch):
    monkeypatch.setattr(access_control, "record_rejection", AsyncMock())
    model = build_model()
    model.slug = "gpt-5.4"
    model.input_price_per_million = Decimal("2.5")
    model.output_price_per_million = Decimal("15")
    model.discount_percent = Decimal("40")
    wallet = {
        "id": "wallet",
        "user_id": "user",
        "balance_cents": 1000,
        "available_balance_cents": 1000,
        "reserved_cents": 0,
        "currency": "USD",
    }
    for name, value in {
        "authenticate_api_key": {"id": "key", "user_id": "user"},
        "fetch_profile": {"id": "user"},
        "fetch_wallet": wallet,
        "get_model_by_slug": model,
    }.items():
        monkeypatch.setattr(access_control, name, AsyncMock(return_value=value))
    reserve = AsyncMock(return_value={"reserved": True})
    monkeypatch.setattr(access_control, "reserve_usage", reserve)
    monkeypatch.setattr(access_control, "touch_api_key_last_used", AsyncMock())
    for name in (
        "check_api_rate_limit",
        "acquire_concurrency_slot",
        "release_concurrency_slot",
    ):
        monkeypatch.setattr(access_control, name, Mock())
    provider = AsyncMock(return_value={"choices": [{"message": {"content": "OK"}}]})
    monkeypatch.setattr(chat, "forward_chat_completion", provider)

    async def bill(**kwargs):
        return kwargs["response_payload"]

    monkeypatch.setattr(chat, "bill_non_streaming_response", bill)
    return model, wallet, reserve, provider


@pytest.mark.parametrize("normal", [False, True])
def test_ten_dollars_funds_small_and_opencode_request(setup, normal):
    model, wallet, reserve, provider = setup
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fixture"},
        json=request_payload(normal),
    )
    assert response.status_code == 200
    provider.assert_awaited_once()
    assert reserve.call_args.args[-1] <= 1000


@pytest.mark.parametrize("balance,normal", [(0, False), (1, True)])
def test_unfunded_request_never_reaches_provider(setup, balance, normal):
    _, wallet, reserve, provider = setup
    wallet.update(balance_cents=balance, available_balance_cents=balance)
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fixture"},
        json=request_payload(normal),
    )
    assert response.status_code == 402
    provider.assert_not_called()
    reserve.assert_not_called()


@pytest.mark.parametrize("balance,expected", [(100, 200), (50, 402)])
def test_reference_one_dollar_customer_sixty_cents(setup, balance, expected):
    model, wallet, reserve, provider = setup
    model.input_price_per_million = Decimal("0")
    model.output_price_per_million = Decimal("1000")
    payload = request_payload()
    payload["max_tokens"] = 1000
    wallet.update(balance_cents=balance, available_balance_cents=balance)
    spending = preflight_spending_details(ChatCompletionRequest(**payload), model)
    assert spending["reference_charge_cents"] == 100
    assert spending["customer_charge_cents"] == 60
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fixture"},
        json=payload,
    )
    assert response.status_code == expected
    assert provider.await_count == (1 if expected == 200 else 0)


def test_dashboard_and_api_both_account_for_holds(setup):
    _, wallet, _, provider = setup
    wallet.update(balance_cents=493, available_balance_cents=13, reserved_cents=480)
    metrics = build_wallet_summary(wallet, [])["metrics"]
    assert metrics["current_balance_cents"] == 493
    assert metrics["available_balance_cents"] == 13
    assert metrics["reserved_cents"] == 480
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fixture"},
        json=request_payload(True),
    )
    assert response.status_code == 402
    provider.assert_not_called()


@pytest.mark.parametrize("balance", [0, 1, 100, 1000])
def test_opencode_and_powershell_same_request_same_decision(setup, balance):
    _, wallet, _, _ = setup
    wallet.update(balance_cents=balance, available_balance_cents=balance)
    client = TestClient(app)
    results = [
        client.post(
            "/v1/chat/completions",
            headers={"Authorization": "Bearer fixture", "User-Agent": agent},
            json=request_payload(True),
        ).status_code
        for agent in ("opencode", "PowerShell")
    ]
    assert results[0] == results[1]


@pytest.mark.parametrize(
    "kind,release",
    [
        (400, True),
        (401, True),
        (404, True),
        (429, True),
        (500, False),
        (502, False),
        ("read_timeout", False),
        ("connect", True),
    ],
)
def test_hold_release_requires_no_consumption_evidence(monkeypatch, kind, release):
    rpc = AsyncMock()
    monkeypatch.setattr(access_control, "release_unconsumed_usage", rpc)
    req = httpx.Request("POST", "https://example.invalid")
    if kind == "read_timeout":
        cause = httpx.ReadTimeout("timeout", request=req)
    elif kind == "connect":
        cause = httpx.ConnectError("connect", request=req)
    else:
        cause = httpx.HTTPStatusError(
            "rejected", request=req, response=httpx.Response(kind, request=req)
        )
    outer = RuntimeError("safe provider error")
    outer.__cause__ = cause
    authz = SimpleNamespace(
        request_id="req_test", api_key={"id": "key", "user_id": "user"}
    )
    asyncio.run(access_control.release_rejected_request(authz, outer))
    assert rpc.await_count == (1 if release else 0)


def test_rejected_provider_releases_hold_through_route(setup, monkeypatch):
    _, _, _, provider = setup
    rpc = AsyncMock()
    monkeypatch.setattr(access_control, "release_unconsumed_usage", rpc)
    req = httpx.Request("POST", "https://example.invalid")
    cause = httpx.HTTPStatusError(
        "rejected", request=req, response=httpx.Response(400, request=req)
    )
    from app.core.errors import OpenAIAPIError

    error = OpenAIAPIError(
        "Provider unavailable",
        error_type="api_error",
        code="provider_unavailable",
        status_code=502,
    )
    error.__cause__ = cause
    provider.side_effect = error
    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer fixture"},
        json=request_payload(True),
    )
    assert response.status_code == 502
    rpc.assert_awaited_once()
