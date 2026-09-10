import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi import status as http_status

from app.core.errors import OpenAIAPIError
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.models.pricing import RequestChargeBreakdown
from app.models.usage import UsageMetrics
from app.models.usage import UsageChargeResult
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.repositories.usage import record_usage_charge as record_usage_charge_rpc
from app.services.pricing import calculate_pricing_breakdown
from app.services.pricing import estimate_customer_charge_cents
from app.services.pricing import estimate_text_tokens
from app.services.token_budget import input_budgets


class UsageChargeError(Exception):
    pass


def extract_usage_metrics(
    payload: dict[str, Any], request: ChatCompletionRequest | None = None
) -> UsageMetrics:
    usage = payload.get("usage") if isinstance(payload, dict) else None
    if isinstance(usage, dict):
        input_tokens = usage.get("prompt_tokens", usage.get("input_tokens"))
        output_tokens = usage.get("completion_tokens", usage.get("output_tokens"))
        details = (
            usage.get("prompt_tokens_details")
            or usage.get("input_tokens_details")
            or {}
        )
        cached_input_tokens = details.get(
            "cached_tokens", usage.get("cached_input_tokens", 0)
        )
        return UsageMetrics(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
        )

    # Never invent usage from characters: tool/reasoning tokens cannot be recovered that way.
    raise OpenAIAPIError(
        "Provider response did not include usage details.",
        error_type="api_error",
        code="missing_usage",
        status_code=http_status.HTTP_502_BAD_GATEWAY,
    )


def preflight_spending_details(
    request: ChatCompletionRequest, model: CatalogModel
) -> dict[str, int]:
    # Conservative text-only budget includes tool schemas and message overhead.
    payload = request.model_dump(exclude_none=True)
    for message in request.messages:
        if message.content is not None and not isinstance(message.content, str):
            raise OpenAIAPIError(
                "Only text messages are supported for metered requests.",
                error_type="invalid_request_error",
                code="unsupported_content",
                status_code=400,
            )
    if payload.get("n", 1) != 1:
        raise OpenAIAPIError(
            "Only one completion per request is supported.",
            error_type="invalid_request_error",
            code="unsupported_n",
            status_code=400,
        )
    input_budget, reservation_input_budget, estimator = input_budgets(request)
    output_budget = request.max_completion_tokens or request.max_tokens or 1024
    if payload.get("service_tier") not in (None, "default"):
        raise OpenAIAPIError(
            "Only standard service pricing is supported.",
            error_type="invalid_request_error",
            code="unsupported_service_tier",
            status_code=400,
        )
    if (
        input_budget > model.pricing_max_input_tokens
        or output_budget > model.pricing_max_output_tokens
    ):
        raise OpenAIAPIError(
            f"Request exceeds the configured pricing tier limits: estimated input {input_budget} "
            f"(limit {model.pricing_max_input_tokens}); requested output {output_budget} "
            f"(limit {model.pricing_max_output_tokens}). Input estimator: {estimator}. "
            "Compact the conversation (/compact or /new) or reduce the output allowance. "
            "No inference was started or charge created.",
            error_type="invalid_request_error",
            code="pricing_limit_exceeded",
            status_code=400,
        )
    usage = UsageMetrics(
        input_tokens=reservation_input_budget,
        output_tokens=max(output_budget, 0),
        cached_input_tokens=0,
    )
    pricing = calculate_pricing_breakdown(model, usage)
    return {
        "input_token_estimate": input_budget,
        "reservation_input_budget": reservation_input_budget,
        "max_output_tokens": output_budget,
        "reference_charge_cents": pricing.reference_charge_cents,
        "customer_charge_cents": pricing.customer_charge_cents,
    }


def estimate_preflight_charge_cents(
    request: ChatCompletionRequest, model: CatalogModel
) -> int:
    return preflight_spending_details(request, model)["customer_charge_cents"]


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
    if (
        usage.input_tokens > model.pricing_max_input_tokens
        or usage.output_tokens > model.pricing_max_output_tokens
    ):
        raise OpenAIAPIError(
            "Provider usage exceeded the authorized pricing tier.",
            error_type="api_error",
            code="usage_reconciliation_required",
            status_code=502,
        )
    pricing = calculate_pricing_breakdown(model, usage)
    try:
        payload = await record_usage_charge_rpc(
            user_id=user_id,
            api_key_id=api_key_id,
            model_id=model.id,
            request_id=request_id,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cached_input_tokens=usage.cached_input_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
            reference_charge_cents=pricing.reference_charge_cents,
            customer_charge_cents=pricing.customer_charge_cents,
            customer_savings_cents=pricing.customer_savings_cents,
            provider_cost_cents=pricing.provider_cost_cents,
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
                status_code=http_status.HTTP_402_PAYMENT_REQUIRED,
            ) from exc
        raise OpenAIAPIError(
            "Billing is temporarily unavailable.",
            error_type="api_error",
            code="billing_unavailable",
            status_code=503,
        ) from exc

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
    usage_payload = None
    buffer = b""
    done = False
    async for chunk in source:
        buffer += chunk
        if len(buffer) > 2_000_000:
            raise OpenAIAPIError(
                "Provider stream frame too large.",
                error_type="api_error",
                code="invalid_stream",
                status_code=502,
            )
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            line = line.rstrip(b"\r")
            if not line.startswith(b"data:"):
                continue
            body = line[5:].strip()
            if body == b"[DONE]":
                done = True
                continue
            try:
                event = json.loads(body)
            except (ValueError, UnicodeError) as exc:
                raise OpenAIAPIError(
                    "Invalid provider stream.",
                    error_type="api_error",
                    code="invalid_stream",
                    status_code=502,
                ) from exc
            if event.get("error"):
                raise OpenAIAPIError(
                    "Provider stream failed.",
                    error_type="api_error",
                    code="provider_unavailable",
                    status_code=502,
                )
            if event.get("usage") is not None:
                usage_payload = event
            safe = {
                key: value
                for key, value in event.items()
                if key
                in {"id", "object", "created", "choices", "usage", "system_fingerprint"}
            }
            safe["model"] = model.slug
            yield ("data: " + json.dumps(safe) + "\n\n").encode()
    if not done:
        raise OpenAIAPIError(
            "Provider stream interrupted.",
            error_type="api_error",
            code="invalid_stream",
            status_code=502,
        )
    payload = usage_payload or {}
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
    # A client must not see successful completion before billing succeeds.
    yield b"data: [DONE]\n\n"


def _set_usage_payload(
    payload: dict[str, Any], box: dict[str, dict[str, Any] | None]
) -> None:
    box["payload"] = payload


def _capture_stream_state(
    chunk: bytes, output_parts: list[str], set_usage_payload
) -> None:
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
