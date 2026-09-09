from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.core.errors import OpenAIAPIError
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services import access_control
from app.api.routes import chat
from test_pricing import build_model


@pytest.fixture
def pipeline(monkeypatch):
    mocks = {
        "authenticate_api_key": AsyncMock(return_value={"id":"key", "user_id":"user"}),
        "fetch_profile": AsyncMock(return_value={"id":"user"}),
        "fetch_wallet": AsyncMock(return_value={"balance_cents":500}),
        "get_model_by_slug": AsyncMock(return_value=build_model()),
        "touch_api_key_last_used": AsyncMock(), "reserve_usage": AsyncMock(),
        "check_api_rate_limit": Mock(), "acquire_concurrency_slot": Mock(), "release_concurrency_slot": Mock(),
    }
    for name, mock in mocks.items():
        monkeypatch.setattr(access_control, name, mock)
    provider = AsyncMock(return_value={"choices":[],"usage":{"prompt_tokens":1,"completion_tokens":1}})
    monkeypatch.setattr(chat,"forward_chat_completion",provider)
    return mocks, provider


@pytest.mark.parametrize("failure,expected", [("key",401),("user",403),("model",404),("zero",402),("funds",402),("rate",429),("concurrency",429),("reservation",402),("size",413)])
def test_rejection_never_calls_provider(pipeline,monkeypatch,failure,expected):
    mocks, provider = pipeline
    if failure == "key": mocks["authenticate_api_key"].return_value = None
    if failure == "user": mocks["fetch_profile"].return_value = None
    if failure == "model": mocks["get_model_by_slug"].return_value = None
    if failure == "zero": mocks["fetch_wallet"].return_value = {"balance_cents":0}
    if failure == "funds":
        mocks["fetch_wallet"].return_value = {"balance_cents":1}
        model = build_model(); model.input_price_per_million = 50000
        mocks["get_model_by_slug"].return_value = model
    if failure in {"rate","concurrency"}:
        name = "check_api_rate_limit" if failure == "rate" else "acquire_concurrency_slot"
        mocks[name].side_effect = OpenAIAPIError("Limited",error_type="rate_limit_error",code="rate_limit_exceeded",status_code=429)
    if failure == "reservation": mocks["reserve_usage"].side_effect = SupabaseRepositoryError("insufficient_balance")
    if failure == "size": monkeypatch.setattr(settings,"api_max_request_bytes",1)
    response = TestClient(app).post("/v1/chat/completions",headers={"Authorization":"Bearer test"},json={"model":"test","messages":[{"role":"user","content":"Hello"}],"max_completion_tokens":16})
    assert response.status_code == expected
    provider.assert_not_called()


def test_stream_slot_retained_until_iteration_finishes(monkeypatch):
    from types import SimpleNamespace
    released = []
    authz = SimpleNamespace(request_id="r",api_key={"id":"k","user_id":"u"},model=build_model())
    monkeypatch.setattr(chat,"authorize_api_request",AsyncMock(return_value=authz))
    monkeypatch.setattr(chat,"release_authorized_request",lambda _: released.append(True))
    async def source():
        assert not released
        yield b"data: [DONE]\n\n"
        assert not released
    monkeypatch.setattr(chat,"forward_chat_completion_stream",AsyncMock(return_value=source()))
    async def billing(**kwargs): return kwargs["source"]
    monkeypatch.setattr(chat,"bill_streaming_response",billing)
    response = TestClient(app).post("/v1/chat/completions",json={"model":"test","messages":[{"role":"user","content":"Hello"}],"stream":True})
    assert response.status_code == 200
    assert released == [True]
