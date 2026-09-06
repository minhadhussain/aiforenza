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
