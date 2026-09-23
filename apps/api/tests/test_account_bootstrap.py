from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.api.routes import account
from app.api.deps import auth
from app.repositories.supabase_rest import SupabaseRepositoryError


def test_bootstrap_requires_authentication():
    assert TestClient(app).post("/v1/account/bootstrap").status_code == 401


@pytest.mark.parametrize("provider", ["email", "google"])
def test_bootstrap_uses_verified_supabase_identity_for_every_provider(monkeypatch, provider):
    monkeypatch.setattr(auth, "fetch_user_for_token", AsyncMock(return_value={"id": "owner", "email": "owner@example.invalid", "app_metadata": {"provider": provider}}))
    bootstrap = AsyncMock(return_value={"wallet_id": "internal", "trial_granted": True})
    monkeypatch.setattr(account, "bootstrap_user_account", bootstrap)
    result = TestClient(app).post("/v1/account/bootstrap", headers={"Authorization": "Bearer session"}, json={"user_id": "victim", "email": "victim@example.invalid", "amount_cents": 999999})
    assert result.status_code == 200 and result.json() == {"ready": True}
    bootstrap.assert_awaited_once_with("owner", "owner@example.invalid")


@pytest.mark.parametrize("failure", [SupabaseRepositoryError("PRIVATE_DATABASE_DETAILS"), httpx.ReadTimeout("PRIVATE_TRANSPORT_DETAILS")])
def test_bootstrap_failure_is_retryable_and_redacted(monkeypatch, failure):
    monkeypatch.setattr(auth, "fetch_user_for_token", AsyncMock(return_value={"id": "owner", "email": "owner@example.invalid"}))
    monkeypatch.setattr(account, "bootstrap_user_account", AsyncMock(side_effect=failure))
    response = TestClient(app).post("/v1/account/bootstrap", headers={"Authorization": "Bearer session"})
    assert response.status_code == 503 and "PRIVATE" not in response.text


def test_bootstrap_rejects_identity_without_email(monkeypatch):
    monkeypatch.setattr(auth, "fetch_user_for_token", AsyncMock(return_value={"id": "owner"}))
    bootstrap = AsyncMock()
    monkeypatch.setattr(account, "bootstrap_user_account", bootstrap)
    assert TestClient(app).post("/v1/account/bootstrap", headers={"Authorization": "Bearer session"}).status_code == 400
    bootstrap.assert_not_called()
