from typing import Any

from fastapi import status

from app.core.errors import OpenAIAPIError
from app.core.ids import create_request_id
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.repositories.wallets import fetch_wallet
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services.litellm_proxy import LiteLLMProxyError
from app.services.litellm_proxy import create_chat_completion as proxy_chat_completion
from app.services.litellm_proxy import stream_chat_completion as proxy_stream_chat_completion
from app.services.models import ModelCatalogError
from app.services.models import get_model_by_slug
from app.services.usage_records import estimate_preflight_charge_cents
from app.services.usage_records import extract_usage_metrics
from app.services.usage_records import record_usage_charge
from app.services.usage_records import stream_and_charge


def _insufficient_balance() -> OpenAIAPIError:
    return OpenAIAPIError(
        "Insufficient balance. Please add funds to continue.",
        error_type="insufficient_balance",
        code="insufficient_balance",
        status_code=status.HTTP_402_PAYMENT_REQUIRED,
    )


async def validate_model_and_wallet(user_id: str, slug: str) -> tuple[CatalogModel, dict, str]:
    try:
        model = await get_model_by_slug(slug)
    except ModelCatalogError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="model_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if model is None:
        raise OpenAIAPIError(
            f"Model '{slug}' not found.",
            error_type="invalid_request_error",
            code="model_not_found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    try:
        wallet = await fetch_wallet(user_id)
    except SupabaseRepositoryError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="wallet_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if wallet is None or int(wallet.get("balance_cents", 0) or 0) <= 0:
        raise _insufficient_balance()

    return model, wallet, create_request_id()


def ensure_preflight_balance(request: ChatCompletionRequest, model: CatalogModel, wallet: dict) -> None:
    estimated_cents = estimate_preflight_charge_cents(request, model)
    balance_cents = int(wallet.get("balance_cents", 0) or 0)
    if estimated_cents > balance_cents:
        raise _insufficient_balance()


def build_provider_payload(request: ChatCompletionRequest, model: CatalogModel, request_id: str) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    payload["model"] = model.provider_model_id
    payload.setdefault("metadata", {})
    if isinstance(payload["metadata"], dict):
        payload["metadata"]["request_id"] = request_id
        payload["metadata"]["public_model"] = model.slug
    return payload


async def forward_chat_completion(request: ChatCompletionRequest, model: CatalogModel, request_id: str) -> dict[str, Any]:
    payload = build_provider_payload(request, model, request_id)
    try:
        return await proxy_chat_completion(payload)
    except LiteLLMProxyError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="provider_unavailable",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc


async def forward_chat_completion_stream(request: ChatCompletionRequest, model: CatalogModel, request_id: str):
    payload = build_provider_payload(request, model, request_id)
    try:
        return await proxy_stream_chat_completion(payload)
    except LiteLLMProxyError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="provider_unavailable",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc


async def bill_non_streaming_response(
    *,
    request: ChatCompletionRequest,
    response_payload: dict[str, Any],
    user_id: str,
    api_key_id: str,
    model: CatalogModel,
    request_id: str,
) -> dict[str, Any]:
    usage = extract_usage_metrics(response_payload, request=request)
    await record_usage_charge(
        user_id=user_id,
        api_key_id=api_key_id,
        model=model,
        request_id=request_id,
        usage=usage,
        provider_cost_reference=request_id,
        status="completed",
    )
    return response_payload


async def bill_streaming_response(
    *,
    source,
    request: ChatCompletionRequest,
    user_id: str,
    api_key_id: str,
    model: CatalogModel,
    request_id: str,
):
    return stream_and_charge(
        source=source,
        request=request,
        model=model,
        user_id=user_id,
        api_key_id=api_key_id,
        request_id=request_id,
    )
