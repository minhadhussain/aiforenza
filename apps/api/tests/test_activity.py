import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps.auth import get_current_dashboard_user
from app.api.routes import account
from app.repositories import activity
from app.services import access_control
from app.core.errors import OpenAIAPIError


@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_current_dashboard_user] = lambda: {
        "id": "owner",
        "email": "owner@example.invalid",
    }
    fetch = AsyncMock(return_value={"data": [], "total": 0})
    monkeypatch.setattr(account, "fetch_activity", fetch)
    yield TestClient(app), fetch
    app.dependency_overrides.clear()


def test_activity_scope_comes_from_session_not_query(client):
    http, fetch = client
    key = str(uuid4())
    response = http.get(
        f"/v1/dashboard/activity?user_id=other&api_key_id={key}&model=gpt-6-astra&page=2&activity_status=rejected"
    )
    assert response.status_code == 200
    assert response.json()["account"]["id"] == "owner"
    assert fetch.call_args.args == ("owner",)
    assert str(fetch.call_args.kwargs["api_key_id"]) == key
    assert fetch.call_args.kwargs["page"] == 2


@pytest.mark.parametrize(
    "query",
    [
        "page=0",
        "page_size=101",
        "api_key_id=bad",
        "activity_status=secret",
        "as_of=2026-01-01T00:00:00",
        "model=x,or(id.eq.y)",
    ],
)
def test_invalid_history_queries_rejected(client, query):
    http, fetch = client
    assert http.get("/v1/dashboard/activity?" + query).status_code == 422
    fetch.assert_not_called()


def test_operational_audit_failure_does_not_alter_rejection(monkeypatch):
    monkeypatch.setattr(
        activity,
        "execute_rest_rpc",
        AsyncMock(side_effect=RuntimeError("PRIVATE_SECRET")),
    )
    asyncio.run(
        activity.record_rejection(
            request_id="req_fixture",
            user_id="owner",
            api_key_id="key",
            model="gpt-5.4",
            code="pricing_limit_exceeded",
            http_status=400,
        )
    )


def test_preflight_rejection_audited_only_after_authentication(monkeypatch):
    audit = AsyncMock()
    monkeypatch.setattr(access_control, "record_rejection", audit)

    async def reject(**kwargs):
        kwargs["rejection_context"]["api_key"] = {"id": "key", "user_id": "owner"}
        raise OpenAIAPIError(
            "Too large",
            error_type="invalid_request_error",
            code="pricing_limit_exceeded",
        )

    monkeypatch.setattr(access_control, "_authorize_api_request", reject)
    from app.models.openai import ChatCompletionRequest

    req = ChatCompletionRequest(
        model="gpt-5.4", messages=[{"role": "user", "content": "PRIVATE PROMPT"}]
    )
    with pytest.raises(OpenAIAPIError):
        asyncio.run(
            access_control.authorize_api_request(
                authorization="Bearer PRIVATE_KEY", request=req, raw_body=b"{}"
            )
        )
    assert audit.await_count == 1
    assert "PRIVATE" not in str(audit.call_args)


def test_anonymous_rejection_not_attributed(monkeypatch):
    audit = AsyncMock()
    monkeypatch.setattr(access_control, "record_rejection", audit)
    monkeypatch.setattr(
        access_control,
        "_authorize_api_request",
        AsyncMock(
            side_effect=OpenAIAPIError(
                "Invalid key",
                error_type="invalid_request_error",
                code="invalid_api_key",
                status_code=401,
            )
        ),
    )
    with pytest.raises(OpenAIAPIError):
        asyncio.run(
            access_control.authorize_api_request(
                authorization=None, request=None, raw_body=b"{}"
            )
        )
    audit.assert_not_called()
