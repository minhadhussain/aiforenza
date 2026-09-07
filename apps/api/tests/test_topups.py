import json

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_checkout_requires_authenticated_dashboard_user() -> None:
    response = client.post("/v1/topups/checkout", json={"amount_cents": 1000})
    assert response.status_code == 401


def test_checkout_creates_session(monkeypatch) -> None:
    async def fake_get_current_dashboard_user() -> dict:
        return {"id": "user-1", "email": "user@example.com"}

    class Result:
        checkout_url = "https://checkout.stripe.test/session"
        session_id = "cs_test_123"
        amount_cents = 1000
        currency = "USD"

    async def fake_create_checkout_session(*, user_id: str, email: str, amount_cents: int):
        assert user_id == "user-1"
        assert email == "user@example.com"
        assert amount_cents == 1000
        return Result()

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.auth", fromlist=["get_current_dashboard_user"]).get_current_dashboard_user] = fake_get_current_dashboard_user
    monkeypatch.setattr("app.api.routes.topups.create_checkout_session", fake_create_checkout_session)

    response = client.post(
        "/v1/topups/checkout",
        json={"amount_cents": 1000},
        headers={"Authorization": "Bearer test-token"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["session_id"] == "cs_test_123"


def test_webhook_processes_checkout_completion(monkeypatch) -> None:
    class Event:
        id = "evt_test_123"
        type = "checkout.session.completed"
        data = {
            "object": {
                "id": "cs_test_123",
                "payment_intent": "pi_test_123",
                "client_reference_id": "user-1",
                "amount_total": 1000,
                "currency": "usd",
                "metadata": {"user_id": "user-1"},
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

    monkeypatch.setattr("app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature)
    monkeypatch.setattr("app.api.routes.topups.handle_checkout_completed", fake_handle_checkout_completed)

    response = client.post(
        "/v1/stripe/webhook",
        data=b'{"id":"evt_test_123"}',
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["processed"] is True
    assert response.json()["topup_id"] == "topup-1"


def test_webhook_ignores_unrelated_event(monkeypatch) -> None:
    class Event:
        id = "evt_test_ignored"
        type = "payment_intent.created"
        data = {"object": {}}

    def fake_verify_webhook_signature(payload: bytes, signature: str | None):
        return Event()

    monkeypatch.setattr("app.api.routes.topups.verify_webhook_signature", fake_verify_webhook_signature)

    response = client.post(
        "/v1/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig_test", "Content-Type": "application/json"},
    )

    assert response.status_code == 200
    assert response.json()["ignored"] is True
