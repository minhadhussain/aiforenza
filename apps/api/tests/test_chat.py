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


def test_chat_completion_rejects_oversized_request_before_provider(monkeypatch) -> None:
    async def fake_authorize_api_request(**kwargs):
        from app.core.errors import OpenAIAPIError
        from fastapi import status

        raise OpenAIAPIError(
            "Request body is too large.",
            error_type="invalid_request_error",
            code="request_too_large",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )

    async def fake_forward_chat_completion(*args, **kwargs):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "request_too_large"


def test_chat_completion_returns_provider_payload(monkeypatch) -> None:
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

    class Authz:
        request_id = "req_test123"
        api_key = {"id": "key-1", "user_id": "user-1"}
        user = {"id": "user-1", "email": "user@example.com"}
        model = Model()
        wallet = {"balance_cents": 500}
        estimated_charge_cents = 0

    async def fake_authorize_api_request(**kwargs):
        return Authz()

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

    released = {"called": False}

    def fake_release_authorized_request(authz):
        released["called"] = True

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)
    monkeypatch.setattr("app.api.routes.chat.bill_non_streaming_response", fake_bill_non_streaming_response)
    monkeypatch.setattr("app.api.routes.chat.release_authorized_request", fake_release_authorized_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_test123"
    assert response.json()["choices"][0]["message"]["content"] == "Hi"
    assert released["called"] is True


def test_chat_completion_streams_provider_chunks(monkeypatch) -> None:
    class Model:
        provider_model_id = "azure/gpt-5.6-luna"
        input_price_per_million = 0
        output_price_per_million = 0
        cached_input_price_per_million = 0
        customer_input_price_per_million = 0
        customer_output_price_per_million = 0
        customer_cached_input_price_per_million = 0
        id = "model-1"

    class Authz:
        request_id = "req_stream123"
        api_key = {"id": "key-1", "user_id": "user-1"}
        user = {"id": "user-1", "email": "user@example.com"}
        model = Model()
        wallet = {"balance_cents": 500}
        estimated_charge_cents = 0

    async def fake_authorize_api_request(**kwargs):
        return Authz()

    async def fake_forward_stream(request, model, request_id: str):
        async def iterator():
            yield b"data: {\"id\":\"chunk-1\"}\n\n"
            yield b"data: [DONE]\n\n"

        return iterator()

    async def fake_bill_streaming_response(**kwargs):
        assert kwargs["api_key_id"] == "key-1"
        return kwargs["source"]

    released = {"called": False}

    def fake_release_authorized_request(authz):
        released["called"] = True

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion_stream", fake_forward_stream)
    monkeypatch.setattr("app.api.routes.chat.bill_streaming_response", fake_bill_streaming_response)
    monkeypatch.setattr("app.api.routes.chat.release_authorized_request", fake_release_authorized_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "stream": True, "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "req_stream123"
    assert "data: [DONE]" in response.text
    assert released["called"] is True


def test_chat_completion_rejects_insufficient_preflight_balance(monkeypatch) -> None:
    async def fake_authorize_api_request(**kwargs):
        from app.core.errors import OpenAIAPIError
        from fastapi import status

        raise OpenAIAPIError(
            "Insufficient balance. Please add funds to continue.",
            error_type="insufficient_balance",
            code="insufficient_balance",
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
        )

    async def fake_forward_chat_completion(*args, **kwargs):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_balance"


def test_chat_completion_returns_model_not_found(monkeypatch) -> None:
    async def fake_authorize_api_request(**kwargs):
        from app.core.errors import OpenAIAPIError
        from fastapi import status

        raise OpenAIAPIError(
            "Model 'not-a-real-model' not found.",
            error_type="invalid_request_error",
            code="model_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    async def fake_forward_chat_completion(*args, **kwargs):
        raise AssertionError("provider should not be called")

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "not-a-real-model", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "model_not_found"


def test_chat_completion_returns_insufficient_balance_when_charge_record_fails(monkeypatch) -> None:
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

    class Authz:
        request_id = "req_charge_fail"
        api_key = {"id": "key-1", "user_id": "user-1"}
        user = {"id": "user-1", "email": "user@example.com"}
        model = Model()
        wallet = {"balance_cents": 500}
        estimated_charge_cents = 0

    async def fake_authorize_api_request(**kwargs):
        return Authz()

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

    released = {"called": False}

    def fake_release_authorized_request(authz):
        released["called"] = True

    monkeypatch.setattr("app.api.routes.chat.authorize_api_request", fake_authorize_api_request)
    monkeypatch.setattr("app.api.routes.chat.forward_chat_completion", fake_forward_chat_completion)
    monkeypatch.setattr("app.api.routes.chat.bill_non_streaming_response", fake_bill_non_streaming_response)
    monkeypatch.setattr("app.api.routes.chat.release_authorized_request", fake_release_authorized_request)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer demo"},
        json={"model": "gpt-5.6-luna", "messages": [{"role": "user", "content": "Hello"}]},
    )

    assert response.status_code == 402
    assert response.json()["error"]["code"] == "insufficient_balance"
    assert released["called"] is True
