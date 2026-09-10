from typing import Any

from fastapi import status

from app.core.errors import OpenAIAPIError
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.services.provider_gateway import ProviderGatewayError
from app.services.provider_gateway import (
    create_chat_completion as proxy_chat_completion,
)
from app.services.provider_gateway import (
    stream_chat_completion as proxy_stream_chat_completion,
)
from app.services.usage_records import extract_usage_metrics
from app.services.usage_records import record_usage_charge
from app.services.usage_records import stream_and_charge


def build_provider_payload(
    request: ChatCompletionRequest, model: CatalogModel, request_id: str
) -> dict[str, Any]:
    payload = request.model_dump(exclude_none=True)
    # OpenAI-compatible SDKs can serialize this Responses-only client option.
    # Chat Completions has no reasoning-summary field; keep reasoning_effort intact.
    payload.pop("reasoningSummary", None)
    # Preserve the same allowance/precedence as preflight; GPT-5.4 rejects max_tokens.
    if request.model == "gpt-5.4" and request.max_tokens is not None:
        payload["max_completion_tokens"] = (
            request.max_completion_tokens or request.max_tokens
        )
        payload.pop("max_tokens", None)
    payload["model"] = model.provider_model_id
    if request.max_tokens is None and request.max_completion_tokens is None:
        payload["max_completion_tokens"] = 1024
    if request.stream:
        payload["stream_options"] = {"include_usage": True}
    return payload


async def forward_chat_completion(
    request: ChatCompletionRequest, model: CatalogModel, request_id: str
) -> dict[str, Any]:
    payload = build_provider_payload(request, model, request_id)
    try:
        return await proxy_chat_completion(payload)
    except ProviderGatewayError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="provider_unavailable",
            status_code=status.HTTP_502_BAD_GATEWAY,
        ) from exc


async def forward_chat_completion_stream(
    request: ChatCompletionRequest, model: CatalogModel, request_id: str
):
    payload = build_provider_payload(request, model, request_id)
    try:
        return await proxy_stream_chat_completion(payload)
    except ProviderGatewayError as exc:
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
    # Return the public model name, not provider routing/debug metadata.
    return {
        **{
            key: value
            for key, value in response_payload.items()
            if key
            in {
                "id",
                "object",
                "created",
                "choices",
                "usage",
                "system_fingerprint",
                "service_tier",
            }
        },
        "model": model.slug,
    }


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
