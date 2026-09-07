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
            input_price_per_million = 0
            output_price_per_million = 0
            cached_input_price_per_million = 0
            customer_input_price_per_million = 0
            customer_output_price_per_million = 0
            customer_cached_input_price_per_million = 0
            id = "model-1"

        return Model(), {"balance_cents": 500}, "req_test123"

    async def fake_forward_chat_completion(request, model, request_id: str) -> dict:
        assert model.provider_model_id == "azure/gpt-5.6-luna"
        assert request_id == "req_test123"
        return {
            "id": "chatcmpl_test",
            "object": "chat.completion",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "prompt_tokens_details": {"cached_tokens": 0}},
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
        }

    async def fake_bill_non_streaming_response(**kwargs):
        assert kwargs["api_key_id"] == "key-1"
        return kwargs["response_payload"]

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)
    monkeypatch.setattr("app.api.routes.chat.bill_non_streaming_response", fake_bill_non_streaming_response)

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
            input_price_per_million = 0
            output_price_per_million = 0
            cached_input_price_per_million = 0
            customer_input_price_per_million = 0
            customer_output_price_per_million = 0
            customer_cached_input_price_per_million = 0
            id = "model-1"

        return Model(), {"balance_cents": 500}, "req_stream123"

    async def fake_forward_stream(request, model, request_id: str):
        async def iterator():
            yield b"data: {\"id\":\"chunk-1\"}\n\n"
            yield b"data: [DONE]\n\n"

        return iterator()

    async def fake_bill_streaming_response(**kwargs):
        assert kwargs["api_key_id"] == "key-1"
        return kwargs["source"]

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion_stream", fake_forward_stream)
    monkeypatch.setattr("app.api.routes.chat.bill_streaming_response", fake_bill_streaming_response)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "stream": True, "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_stream123"
    assert "data: [DONE]" in response.text


def test_chat_completion_rejects_insufficient_preflight_balance(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_validate_model_and_wallet(user_id: str, slug: str):
        class Model:
            provider_model_id = "azure/gpt-5.6-luna"
            input_price_per_million = 1000
            output_price_per_million = 1000
            cached_input_price_per_million = 0
            customer_input_price_per_million = 1000
            customer_output_price_per_million = 1000
            customer_cached_input_price_per_million = 0

        return Model(), {"balance_cents": 0}, "req_lowbal"

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_balance"


def test_chat_completion_returns_model_not_found(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_validate_model_and_wallet(user_id: str, slug: str):
        from app.core.errors import OpenAIAPIError
        from fastapi import status

        raise OpenAIAPIError(
            f"Model '{slug}' not found.",
            error_type="invalid_request_error",
            code="model_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "not-a-real-model", "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_chat_completion_returns_insufficient_balance_when_charge_record_fails(monkeypatch) -> None:
    async def fake_get_current_api_key() -> dict:
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_validate_model_and_wallet(user_id: str, slug: str):
        class Model:
            slug = "gpt-5.6-luna"
            provider_model_id = "azure/gpt-5.6-luna"
            input_price_per_million = 0
            output_price_per_million = 0
            cached_input_price_per_million = 0
            customer_input_price_per_million = 0
            customer_output_price_per_million = 0
            customer_cached_input_price_per_million = 0
            id = "model-1"

        return Model(), {"balance_cents": 500}, "req_charge_fail"

    async def fake_forward_chat_completion(request, model, request_id: str) -> dict:
        return {
            "id": "chatcmpl_test",
            "object": "chat.completion",
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "prompt_tokens_details": {"cached_tokens": 0}},
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi"}, "finish_reason": "stop"}],
        }

    async def fake_bill_non_streaming_response(**kwargs):
        from app.core.errors import OpenAIAPIError
        from fastapi import status

        raise OpenAIAPIError(
            "Insufficient balance. Please add funds to continue.",
            error_type="insufficient_balance",
            code="insufficient_balance",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )

    app.dependency_overrides.clear()
    app.dependency_overrides[__import__("app.api.deps.api_keys", fromlist=["get_current_api_key"]).get_current_api_key] = fake_get_current_api_key
    monkeypatch.setattr("app.api.routes.chat.validate_model_and_wallet", fake_validate_model_and_wallet)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)
    monkeypatch.setattr("app.api.routes.chat.bill_non_streaming_response", fake_bill_non_streaming_response)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_balance"
