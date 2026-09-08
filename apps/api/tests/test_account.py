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

    async def fake_fetch_usage_summary(user_id: str) -> dict:
        assert user_id == "user-123"
        return {
            "today_usage_cents": 11,
            "month_usage_cents": 42,
            "api_request_count": 3,
        }

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)
    monkeypatch.setattr("app.api.routes.account.bootstrap_user_account", fake_bootstrap_user_account)
    monkeypatch.setattr("app.api.routes.account.fetch_wallet", fake_fetch_wallet)
    monkeypatch.setattr("app.api.routes.account.fetch_transactions", fake_fetch_transactions)
    monkeypatch.setattr("app.api.routes.account.fetch_usage_summary", fake_fetch_usage_summary)

    response = client.get(
        "/v1/dashboard/overview",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["wallet"]["balance_cents"] == 500
    assert payload["bootstrap"]["trial_granted"] is True
    assert payload["metrics"]["trial_credit_granted"] is True
    assert payload["metrics"]["today_usage_cents"] == 11
    assert payload["metrics"]["month_usage_cents"] == 42
    assert payload["metrics"]["api_request_count"] == 3


def test_dashboard_transactions_returns_ledger_rows(monkeypatch) -> None:
    async def fake_fetch_user_for_token(access_token: str) -> dict:
        return {"id": "user-123", "email": "user@example.com"}

    async def fake_fetch_transactions(user_id: str, limit: int = 50) -> list[dict]:
        assert user_id == "user-123"
        return [
            {
                "id": "tx-1",
                "type": "TOPUP",
                "amount_cents": 1000,
                "balance_after_cents": 1500,
                "description": "Stripe wallet top-up",
                "reference_id": "stripe:cs_test",
                "created_at": "2026-09-07T00:00:00Z",
            }
        ]

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)
    monkeypatch.setattr("app.api.routes.account.fetch_transactions", fake_fetch_transactions)

    response = client.get(
        "/v1/dashboard/transactions",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["type"] == "TOPUP"


def test_dashboard_usage_returns_usage_rows(monkeypatch) -> None:
    async def fake_fetch_user_for_token(access_token: str) -> dict:
        return {"id": "user-123", "email": "user@example.com"}

    async def fake_fetch_usage_records(user_id: str, limit: int = 50) -> list[dict]:
        assert user_id == "user-123"
        return [
            {
                "id": "usage-1",
                "request_id": "req_123",
                "input_tokens": 12,
                "output_tokens": 8,
                "cached_input_tokens": 2,
                "customer_charge_cents": 11,
                "status": "completed",
                "created_at": "2026-09-07T00:00:00Z",
                "model": {"slug": "gpt-5.6-luna", "display_name": "GPT-5.6 Luna"},
            }
        ]

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)
    monkeypatch.setattr("app.api.routes.account.fetch_usage_records", fake_fetch_usage_records)

    response = client.get(
        "/v1/dashboard/usage",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["customer_charge_cents"] == 11


def test_dashboard_models_returns_customer_pricing(monkeypatch) -> None:
    async def fake_fetch_user_for_token(access_token: str) -> dict:
        return {"id": "user-123", "email": "user@example.com"}

    class Model:
        id = "model-1"
        slug = "gpt-5.6-luna"
        display_name = "GPT-5.6 Luna"
        provider = "azure"
        input_price_per_million = 10
        output_price_per_million = 20
        cached_input_price_per_million = 5
        discount_percent = 40
        customer_input_price_per_million = 5000
        customer_output_price_per_million = 5000
        customer_cached_input_price_per_million = 2500

    async def fake_fetch_enabled_models() -> list:
        return [Model()]

    monkeypatch.setattr("app.api.deps.auth.fetch_user_for_token", fake_fetch_user_for_token)
    monkeypatch.setattr("app.api.routes.account.fetch_enabled_models", fake_fetch_enabled_models)

    response = client.get(
        "/v1/dashboard/models",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json()["data"][0]["slug"] == "gpt-5.6-luna"
    assert response.json()["data"][0]["customer_input_price_per_million"] == 5000
