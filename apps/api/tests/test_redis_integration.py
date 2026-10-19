import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from redis import Redis
from app.services import rate_limit
from app.core.config import settings
from app.core.errors import OpenAIAPIError


def test_atomic_redis_limits(monkeypatch):
    if os.getenv("RUN_REDIS_TESTS") != "1":
        pytest.skip("Set RUN_REDIS_TESTS=1 with local Redis running")
    client = Redis.from_url("redis://127.0.0.1:6379/0",decode_responses=True)
    user, key = uuid4().hex, uuid4().hex
    monkeypatch.setattr(rate_limit,"_client",lambda:client)
    monkeypatch.setattr(settings,"api_max_concurrent_requests",1)
    monkeypatch.setattr(settings,"api_requests_per_minute_per_key",1)
    monkeypatch.setattr(settings,"api_requests_per_minute_per_user",1)
    def acquire(_):
        try:
            rate_limit.acquire_concurrency_slot(user_id=user,api_key_id=key)
            return True
        except OpenAIAPIError as exc:
            assert exc.status_code == 429
            return False
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            assert list(pool.map(acquire, range(2))).count(True) == 1
        rate_limit.release_concurrency_slot(user_id=user,api_key_id=key)
        assert acquire(0)
        rate_limit.release_concurrency_slot(user_id=user,api_key_id=key)
        rate_limit.check_api_rate_limit(user_id=user,api_key_id=key)
        with pytest.raises(OpenAIAPIError) as exc:
            rate_limit.check_api_rate_limit(user_id=user,api_key_id=key)
        assert exc.value.status_code == 429
    finally:
        # Only delete this test's hashed identities, never flush shared Redis.
        for pattern in (f"*{rate_limit._safe_key(user)}*",f"*{rate_limit._safe_key(key)}*"):
            for item in client.scan_iter(match=pattern):
                client.delete(item)
        client.close()


def test_claim_throttle_survives_new_clients_sessions_and_ip_headers(monkeypatch):
    if os.getenv("RUN_REDIS_TESTS") != "1":
        pytest.skip("Set RUN_REDIS_TESTS=1 with local Redis running")
    from unittest.mock import AsyncMock
    from fastapi.testclient import TestClient
    from app.api.deps.auth import get_current_dashboard_user
    from app.api.routes import hackathon
    from app.main import app
    from app.repositories.supabase_rest import SupabaseRepositoryError

    client = Redis.from_url("redis://127.0.0.1:6379/0", decode_responses=True)
    owner = uuid4().hex
    key = "hackathon-claim:" + owner
    monkeypatch.setattr(rate_limit, "_client", lambda: client)
    monkeypatch.setattr(settings, "api_requests_per_minute_per_user", 1)
    monkeypatch.setattr(settings, "api_requests_per_minute_per_key", 1)
    # Auth has resolved multiple login sessions to the same verified account.
    monkeypatch.setitem(app.dependency_overrides, get_current_dashboard_user, lambda: {"id": owner})
    monkeypatch.setattr(hackathon, "fetch_profile", AsyncMock(return_value={"id": owner}))
    rpc = AsyncMock(side_effect=SupabaseRepositoryError("team_already_claimed"))
    monkeypatch.setattr(hackathon, "claim_team", rpc)
    try:
        for index in range(4):
            with TestClient(app) as http:
                result = http.post("/v1/hackathon/claim", headers={
                    "Authorization": f"Bearer fixture-session-{index}",
                    "X-Forwarded-For": f"198.51.100.{index + 1}",
                    "Cookie": f"fresh-browser={index}",
                }, json={"team_id": "HACK-001"})
            assert result.status_code == (409 if index == 0 else 429)
            assert "plaintext_key" not in result.text
        rpc.assert_awaited_once()
    finally:
        for pattern in (f"*{rate_limit._safe_key(owner)}*", f"*{rate_limit._safe_key(key)}*"):
            for item in client.scan_iter(match=pattern):
                client.delete(item)
        client.close()
