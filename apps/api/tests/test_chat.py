from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_chat_completion_requires_api_key() -> None:
    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_api_key"


def test_chat_completion_returns_provider_payload(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_validate_model_and_wallet(user_id: str, slug: str):
        assert user_id == "user-1"
        assert slug == "gpt-5.6-luna"

        class Model:
            slug = "gpt-5.6-luna"
            provider_model_id = "azure/gpt-5.6-luna"

        return Model(), {"balance_cents": 500}, "req_test123"

    async def fake_forward_chat_completion(request, model, request_id: str) -> dict:
        assert model.provider_model_id == "azure/gpt-5.6-luna"
        assert request_id == "req_test123"
        return {
            "id": "chatcmpl_test",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
        }

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_test123"
    assert response.json()["choices"][0]["message"]["content"] == "Hi"


def test_chat_completion_streams_provider_chunks(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_validate_model_and_wallet(user_id: str, slug: str):
        class Model:
            provider_model_id = "azure/gpt-5.6-luna"

        return Model(), {"balance_cents": 500}, "req_stream123"

    async def fake_forward_stream(request, model, request_id: str):
        async def iterator():
            yield b"data: {\"id\":\"chunk-1\"}\n\n"
            yield b"data: [DONE]\n\n"

        return iterator()

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion_stream", fake_forward_stream)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "stream": True, "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_stream123"
    assert "data: [DONE]" in response.text
