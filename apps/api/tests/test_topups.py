import json
from unittest.mock import AsyncMock

import pytest

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_checkout_requires_authenticated_dashboard_user() -> None:
    response = client.post("/v1/topups/checkout", json={"package_id": "starter_10"})
    assert response.status_code == 401


def test_checkout_creates_session(monkeypatch) -> None:
    async def fake_get_current_dashboard_user() -> dict:
        return {"id": "user-1", "email": "user@example.com"}

    async def fake_bootstrap_user_account(user_id: str, email: str) -> dict:
        assert user_id == "user-1"
        assert email == "user@example.com"
        return {
            "wallet_id": "wallet-1",
            "balance_cents": 500,
            "currency": "USD",
            "trial_granted": False,
        }

    class Result:
        checkout_url = "https://checkout.stripe.test/session"
        session_id = "cs_test_123"
        package_id = "starter_10"
        package_value_usd_cents = 1000
        stripe_amount_inr = 83500
        currency = "INR"

    async def fake_create_checkout_session(
        *, user_id: str, email: str, package_id: str
    ):
        assert user_id == "user-1"
        assert email == "user@example.com"
        assert package_id == "starter_10"
        return Result()

    app.dependency_overrides.clear()
    app.dependency_overrides[
        __import__(
            "app.api.deps.auth", fromlist=["get_current_dashboard_user"]
        ).get_current_dashboard_user
    ] = fake_get_current_dashboard_user
    monkeypatch.setattr(
        "app.api.routes.topups.bootstrap_user_account", fake_bootstrap_user_account
    )
    monkeypatch.setattr(
        "app.api.routes.topups.create_checkout_session", fake_create_checkout_session
    )

    response = client.post(
        "/v1/topups/checkout",
        json={"package_id": "starter_10"},
        headers={"Authorization": "Bearer test-token"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["session_id"] == "cs_test_123"
    assert response.json()["currency"] == "INR"
    assert response.json()["package_value_usd_cents"] == 1000
    assert response.json()["stripe_amount_inr"] == 83500


@pytest.mark.parametrize(
    "event_type",
    ["checkout.session.completed", "checkout.session.async_payment_succeeded"],
)
def test_webhook_processes_checkout_completion(monkeypatch, event_type) -> None:
    class Event:
        id = "evt_test_123"
        type = event_type
        data = {
            "object": {
                "id": "cs_test_123",
                "payment_intent": "pi_test_123",
                "client_reference_id": "user-1",
                "amount_total": 83500,
                "currency": "inr",
                "mode": "payment",
                "status": "complete",
                "payment_status": "paid",
                "livemode": False,
                "metadata": {
                    "user_id": "user-1",
                    "topup_id": "topup-1",
                    "package_id": "starter_10",
                    "package_value_usd_cents": "1000",
                    "stripe_amount_inr": "83500",
                },
            }
        }

    class Result:
        already_processed = False
        topup_id = "topup-1"

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        assert signature == "sig_test"
        assert payload == b'{"id":"evt_test_123"}'
        return Event()

    async def fake_handle_checkout_completed(event):
        assert event.id == "evt_test_123"
        return Result()

    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature
    )
    monkeypatch.setattr(
        "app.api.routes.topups.handle_checkout_completed",
        fake_handle_checkout_completed,
    )

    response = client.post(
        "/v1/stripe/webhook",
        data=b'{"id":"evt_test_123"}',
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["processed"] is True
    assert response.json()["topup_id"] == "topup-1"


def test_billing_checkout_alias_creates_session(monkeypatch) -> None:
    async def fake_get_current_dashboard_user() -> dict:
        return {"id": "user-1", "email": "user@example.com"}

    async def fake_bootstrap_user_account(user_id: str, email: str) -> dict:
        assert user_id == "user-1"
        assert email == "user@example.com"
        return {
            "wallet_id": "wallet-1",
            "balance_cents": 500,
            "currency": "USD",
            "trial_granted": False,
        }

    class Result:
        checkout_url = "https://checkout.stripe.test/session"
        session_id = "cs_test_123"
        package_id = "starter_25"
        package_value_usd_cents = 2500
        stripe_amount_inr = 208750
        currency = "INR"

    async def fake_create_checkout_session(
        *, user_id: str, email: str, package_id: str
    ):
        assert user_id == "user-1"
        assert email == "user@example.com"
        assert package_id == "starter_25"
        return Result()

    app.dependency_overrides.clear()
    app.dependency_overrides[
        __import__(
            "app.api.deps.auth", fromlist=["get_current_dashboard_user"]
        ).get_current_dashboard_user
    ] = fake_get_current_dashboard_user
    monkeypatch.setattr(
        "app.api.routes.topups.bootstrap_user_account", fake_bootstrap_user_account
    )
    monkeypatch.setattr(
        "app.api.routes.topups.create_checkout_session", fake_create_checkout_session
    )

    response = client.post(
        "/v1/billing/create-checkout-session",
        json={"package_id": "starter_25"},
        headers={"Authorization": "Bearer test-token"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["package_value_usd_cents"] == 2500
    assert response.json()["stripe_amount_inr"] == 208750


def test_webhook_alias_uses_same_processing(monkeypatch) -> None:
    class Event:
        id = "evt_test_aliased"
        type = "checkout.session.completed"
        data = {
            "object": {
                "id": "cs_test_123",
                "payment_intent": "pi_test_123",
                "client_reference_id": "user-1",
                "amount_total": 83500,
                "currency": "inr",
                "mode": "payment",
                "status": "complete",
                "payment_status": "paid",
                "livemode": False,
                "metadata": {
                    "user_id": "user-1",
                    "topup_id": "topup-1",
                    "package_id": "starter_10",
                    "package_value_usd_cents": "1000",
                    "stripe_amount_inr": "83500",
                },
            }
        }

    class Result:
        already_processed = True
        topup_id = "topup-1"

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        return Event()

    async def fake_handle_checkout_completed(event):
        return Result()

    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature
    )
    monkeypatch.setattr(
        "app.api.routes.topups.handle_checkout_completed",
        fake_handle_checkout_completed,
    )

    response = client.post(
        "/v1/webhooks/stripe",
        data=b"{}",
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["already_processed"] is True


def test_missing_webhook_secret_returns_configuration_error(monkeypatch) -> None:
    from app.core.errors import OpenAIAPIError
    from fastapi import status

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        raise OpenAIAPIError(
            "Stripe webhook secret is not configured.",
            error_type="api_error",
            code="stripe_not_configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature
    )

    response = client.post(
        "/v1/webhooks/stripe",
        data=b"{}",
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "stripe_not_configured"


def test_invalid_webhook_signature_returns_400(monkeypatch) -> None:
    from app.core.errors import OpenAIAPIError
    from fastapi import status

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        raise OpenAIAPIError(
            "Invalid Stripe signature.",
            error_type="invalid_request_error",
            code="invalid_webhook",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature
    )

    response = client.post(
        "/v1/webhooks/stripe",
        data=b"{}",
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_webhook"


def test_wrong_currency_or_amount_does_not_credit(monkeypatch) -> None:
    from app.services import stripe_payments

    fetch = AsyncMock(
        return_value={
            "id": "topup-1",
            "user_id": "user-1",
            "package_id": "starter_10",
            "package_value_usd_cents": 1000,
            "stripe_amount_inr": 83500,
            "currency": "USD",
            "stripe_checkout_session_id": "cs_test_123",
            "stripe_payment_intent_id": "pi_test_123",
            "status": "PENDING",
        }
    )
    credit = AsyncMock()
    monkeypatch.setattr(stripe_payments, "fetch_topup_by_id", fetch)
    monkeypatch.setattr(stripe_payments, "complete_topup_record", credit)
    event = type(
        "Event",
        (),
        {
            "id": "evt_test",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_intent": "pi_test_123",
                    "client_reference_id": "user-1",
                    "amount_total": 99999,
                    "currency": "inr",
                    "mode": "payment",
                    "status": "complete",
                    "payment_status": "paid",
                    "livemode": False,
                    "metadata": {
                        "user_id": "user-1",
                        "topup_id": "topup-1",
                        "package_id": "starter_10",
                        "package_value_usd_cents": "1000",
                        "stripe_amount_inr": "83500",
                    },
                }
            },
        },
    )()
    import asyncio

    with pytest.raises(Exception):
        asyncio.run(stripe_payments.handle_checkout_completed(event))
    credit.assert_not_called()


def test_webhook_ignores_unrelated_event(monkeypatch) -> None:
    class Event:
        id = "evt_test_ignored"
        type = "payment_intent.created"
        data = {"object": {}}

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        return Event()

    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature
    )

    response = client.post(
        "/v1/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["ignored"] is True


def test_delayed_unpaid_completion_waits_for_paid_event(monkeypatch):
    from types import SimpleNamespace

    event = SimpleNamespace(
        type="checkout.session.completed", data={"object": {"payment_status": "unpaid"}}
    )
    monkeypatch.setattr(
        "app.api.routes.topups.verify_webhook_signature", lambda *args: event
    )
    credit = AsyncMock()
    monkeypatch.setattr("app.api.routes.topups.handle_checkout_completed", credit)
    response = client.post(
        "/v1/webhooks/stripe", content=b"{}", headers={"Stripe-Signature": "fixture"}
    )
    assert response.status_code == 200 and response.json()["pending_payment"] is True
    credit.assert_not_called()
