from fastapi import status

from app.core.errors import OpenAIAPIError
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.models.openai import ChatMessage
from app.services.access_control import authorize_api_request


def build_request() -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model="gpt-5.6-luna",
        messages=[ChatMessage(role="user", content="Hello")],
        max_completion_tokens=32,
    )


def build_model() -> CatalogModel:
    return CatalogModel(
        id="model-1",
        slug="gpt-5.6-luna",
        display_name="GPT-5.6 Luna",
        provider="azure",
        provider_model_id="gpt-5.6-luna",
        enabled=True,
        input_price_per_million=10,
        output_price_per_million=20,
        cached_input_price_per_million=5,
        discount_percent=40,
        customer_input_price_per_million=6,
        customer_output_price_per_million=12,
        customer_cached_input_price_per_million=3,
    )


def test_authorize_api_request_rejects_rate_limited(monkeypatch) -> None:
    async def fake_authenticate_api_key(api_key: str):
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_fetch_profile(user_id: str):
        return {"id": user_id, "email": "user@example.com"}

    async def fake_fetch_wallet(user_id: str):
        return {"user_id": user_id, "balance_cents": 500}

    def fake_check_api_rate_limit(**kwargs):
        raise OpenAIAPIError(
            "Rate limit exceeded. Please try again later.",
            error_type="rate_limit_error",
            code="rate_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    monkeypatch.setattr("app.services.access_control.authenticate_api_key", fake_authenticate_api_key)
    monkeypatch.setattr("app.services.access_control.fetch_profile", fake_fetch_profile)
    monkeypatch.setattr("app.services.access_control.fetch_wallet", fake_fetch_wallet)
    monkeypatch.setattr("app.services.access_control.check_api_rate_limit", fake_check_api_rate_limit)

    import asyncio

    try:
        asyncio.run(authorize_api_request(authorization="Bearer demo", request=build_request(), raw_body=b"{}"))
        assert False, "expected rate limit error"
    except OpenAIAPIError as exc:
        assert exc.code == "rate_limit_exceeded"


def test_authorize_api_request_rejects_concurrency_limited(monkeypatch) -> None:
    async def fake_authenticate_api_key(api_key: str):
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_fetch_profile(user_id: str):
        return {"id": user_id, "email": "user@example.com"}

    async def fake_fetch_wallet(user_id: str):
        return {"user_id": user_id, "balance_cents": 500}

    def fake_check_api_rate_limit(**kwargs):
        return None

    def fake_acquire_concurrency_slot(**kwargs):
        raise OpenAIAPIError(
            "Rate limit exceeded. Please try again later.",
            error_type="rate_limit_error",
            code="concurrency_limit_exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    monkeypatch.setattr("app.services.access_control.authenticate_api_key", fake_authenticate_api_key)
    monkeypatch.setattr("app.services.access_control.fetch_profile", fake_fetch_profile)
    monkeypatch.setattr("app.services.access_control.fetch_wallet", fake_fetch_wallet)
    monkeypatch.setattr("app.services.access_control.check_api_rate_limit", fake_check_api_rate_limit)
    monkeypatch.setattr("app.services.access_control.acquire_concurrency_slot", fake_acquire_concurrency_slot)

    import asyncio

    try:
        asyncio.run(authorize_api_request(authorization="Bearer demo", request=build_request(), raw_body=b"{}"))
        assert False, "expected concurrency limit error"
    except OpenAIAPIError as exc:
        assert exc.code == "concurrency_limit_exceeded"


def test_authorize_api_request_rejects_zero_balance(monkeypatch) -> None:
    async def fake_authenticate_api_key(api_key: str):
        return {"id": "key-1", "user_id": "user-1"}

    async def fake_fetch_profile(user_id: str):
        return {"id": user_id, "email": "user@example.com"}

    async def fake_fetch_wallet(user_id: str):
        return {"user_id": user_id, "balance_cents": 0}

    async def fake_get_model_by_slug(slug: str):
        return build_model()

    monkeypatch.setattr("app.services.access_control.authenticate_api_key", fake_authenticate_api_key)
    monkeypatch.setattr("app.services.access_control.fetch_profile", fake_fetch_profile)
    monkeypatch.setattr("app.services.access_control.fetch_wallet", fake_fetch_wallet)
    monkeypatch.setattr("app.services.access_control.get_model_by_slug", fake_get_model_by_slug)
    monkeypatch.setattr("app.services.access_control.check_api_rate_limit", lambda **kwargs: None)
    monkeypatch.setattr("app.services.access_control.acquire_concurrency_slot", lambda **kwargs: None)
    monkeypatch.setattr("app.services.access_control.touch_api_key_last_used", lambda *args, **kwargs: None)

    import asyncio

    try:
        asyncio.run(authorize_api_request(authorization="Bearer demo", request=build_request(), raw_body=b"{}"))
        assert False, "expected insufficient balance"
    except OpenAIAPIError as exc:
        assert exc.code == "insufficient_balance"
