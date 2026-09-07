import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import status

from app.core.errors import OpenAIAPIError
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.models.usage import UsageChargeResult
from app.models.usage import UsageMetrics
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.usage import record_usage_charge as record_usage_charge_rpc
from app.services.pricing import calculate_customer_charge
from app.services.pricing import estimate_text_tokens


class UsageChargeError(Exception):
    pass


def extract_usage_metrics(payload: dict[str, Any], request: ChatCompletionRequest | None = None) -> UsageMetrics:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if isinstance(usage, dict):
        input_tokens = int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0)
        output_tokens = int(usage.get("completion_tokens") or usage.get("output_tokens") or 0)
        details = usage.get("prompt_tokens_details") or usage.get("input_tokens_details") or {}
        cached_input_tokens = int(details.get("cached_tokens") or usage.get("cached_input_tokens") or 0)
        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
        )

    if request is None:
        raise OpenAIAPIError(
            "Provider response did not include usage details.",
            error_type="api_error",
            code="missing_usage",
            status_code=status.HTTP_502_BAD_GATEWAY,
        )

    input_text = " ".join(_message_text(message.content) for message in request.messages)
    output_text = _extract_non_streaming_output_text(payload)
    return UsageMetrics(
        input_tokens=estimate_text_tokens(input_text),
        output_tokens=estimate_text_tokens(output_text),
        cached_input_tokens=0,
    )


def estimate_preflight_charge_cents(request: ChatCompletionRequest, model: CatalogModel) -> int:
    input_text = " ".join(_message_text(message.content) for message in request.messages)
    output_budget = request.max_completion_tokens or request.max_tokens or 1024
    usage = UsageMetrics(
        input_tokens=estimate_text_tokens(input_text),
        output_tokens=max(output_budget, 0),
        cached_input_tokens=0,
    )
    return calculate_customer_charge(model, usage).cents


def _message_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return " ".join(parts)
    return ""


def _extract_non_streaming_output_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") if isinstance(payload, dict) else None
    if not isinstance(choices, list):
        return ""

    parts: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            parts.append(message["content"])
        elif isinstance(choice.get("text"), str):
            parts.append(choice["text"])
    return "".join(parts)


async def record_usage_charge(
    *,
    user_id: str,
    api_key_id: str,
    model: CatalogModel,
    request_id: str,
    usage: UsageMetrics,
    provider_cost_reference: str,
    status: str,
) -> UsageChargeResult:
    charge = calculate_customer_charge(model, usage)
    try:
        payload = await record_usage_charge_rpc(
            user_id=user_id,
            api_key_id=api_key_id,
            model_id=model.id,
            request_id=request_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            customer_charge_cents=charge.cents,
            provider_cost_reference=provider_cost_reference,
            status=status,
        )
    except SupabaseRepositoryError as exc:
        message = str(exc)
        if "insufficient_balance" in message:
            raise OpenAIAPIError(
                "Insufficient balance. Please add funds to continue.",
                error_type="insufficient_balance",
                code="insufficient_balance",
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
            ) from exc
        raise UsageChargeError(message) from exc

    return UsageChargeResult.model_validate(payload)


async def stream_and_charge(
    *,
    source: AsyncIterator[bytes],
    request: ChatCompletionRequest,
    model: CatalogModel,
    user_id: str,
    api_key_id: str,
    request_id: str,
) -> AsyncIterator[bytes]:
    usage_payload_box: dict[str, dict[str, Any] | None] = {"payload": None}
    output_parts: list[str] = []

    async for chunk in source:
        _capture_stream_state(chunk, output_parts, lambda payload: _set_usage_payload(payload, usage_payload_box))
        yield chunk

    payload = usage_payload_box["payload"] or {"choices": [{"message": {"content": "".join(output_parts)}}]}
    usage = extract_usage_metrics(payload, request=request)
    await record_usage_charge(
        user_id=user_id,
        api_key_id=api_key_id,
        model=model,
        request_id=request_id,
        usage=usage,
        provider_cost_reference=request_id,
        status="completed",
    )


def _set_usage_payload(payload: dict[str, Any], box: dict[str, dict[str, Any] | None]) -> None:
    box["payload"] = payload


def _capture_stream_state(chunk: bytes, output_parts: list[str], set_usage_payload) -> None:
    text = chunk.decode("utf-8", errors="ignore")
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue
        body = line[6:].strip()
        if not body or body == "[DONE]":
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue

        if isinstance(payload, dict) and payload.get("usage"):
            set_usage_payload(payload)

        for choice in payload.get("choices", []) if isinstance(payload, dict) else []:
            delta = choice.get("delta") if isinstance(choice, dict) else None
            if isinstance(delta, dict) and isinstance(delta.get("content"), str):
                output_parts.append(delta["content"])
