from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_account_requires_bearer_token() -> None:
    response = client.get("/v1/account/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing bearer token."


def test_account_returns_authenticated_user(monkeypatch) -> None:
    async def fake_fetch_user_for_token(access_token: str) -> dict:
        assert access_token == "test-token"
        return {
            "id": "user-123",
            "email": "user@example.com",
            "app_metadata": {"provider": "email"},
            "user_metadata": {"name": "User"},
        }

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)

    response = client.get(
        "/v1/account/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"


def test_dashboard_overview_bootstraps_wallet(monkeypatch) -> None:
    async def fake_fetch_user_for_token(access_token: str) -> dict:
        assert access_token == "test-token"
        return {
            "id": "user-123",
            "email": "user@example.com",
        }

    async def fake_bootstrap_user_account(user_id: str, email: str) -> dict:
        assert user_id == "user-123"
        assert email == "user@example.com"
        return {
            "wallet_id": "wallet-123",
            "balance_cents": 500,
            "currency": "USD",
            "trial_granted": True,
        }

    async def fake_fetch_wallet(user_id: str) -> dict:
        assert user_id == "user-123"
        return {
            "id": "wallet-123",
            "user_id": "user-123",
            "balance_cents": 500,
            "currency": "USD",
            "created_at": "2026-09-07T00:00:00Z",
            "updated_at": "2026-09-07T00:00:00Z",
        }

    async def fake_fetch_transactions(user_id: str) -> list[dict]:
        assert user_id == "user-123"
        return [
            {
                "id": "tx-1",
                "type": "FREE_TRIAL",
                "amount_cents": 500,
                "balance_after_cents": 500,
                "description": "Initial $5.00 trial credit",
                "reference_id": "signup:user-123",
                "created_at": "2026-09-07T00:00:00Z",
            }
        ]

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)
    monkeypatch.setattr("app.api.routes.account.bootstrap_user_account", fake_bootstrap_user_account)
    monkeypatch.setattr("app.api.routes.account.fetch_wallet", fake_fetch_wallet)
    monkeypatch.setattr("app.api.routes.account.fetch_transactions", fake_fetch_transactions)

    response = client.get(
        "/v1/dashboard/overview",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["wallet"]["balance_cents"] == 500
    assert payload["bootstrap"]["trial_granted"] is True
    assert payload["metrics"]["trial_credit_granted"] is True
