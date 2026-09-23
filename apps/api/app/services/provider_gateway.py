from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit
import json
import logging

import httpx

from app.core.config import settings
from app.services.responses_compat import from_responses, stream_to_chat

logger = logging.getLogger("aiforenza.provider")


class ProviderGatewayError(Exception):
    """Only safe public text/codes; never upstream bodies or credentials."""

    def __init__(self, message, *, code="provider_unavailable", status_code=502):
        super().__init__(message)
        self.code = code
        self.status_code = status_code


def _chat_url(api="chat/completions") -> str:
    if settings.azure_endpoint:
        endpoint = settings.azure_endpoint.rstrip("/")
        parsed = urlsplit(endpoint)
        if not settings.azure_api_key or parsed.scheme != "https" or parsed.query or not parsed.path.endswith("/openai/v1"):
            raise ProviderGatewayError("Model provider is not configured correctly.")
        return f"{endpoint}/{api}"
    return f"{settings.litellm_url.rstrip('/')}/v1/{api}"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.azure_endpoint:
        headers["api-key"] = settings.azure_api_key
    elif settings.litellm_master_key:
        headers["Authorization"] = f"Bearer {settings.litellm_master_key}"
    return headers


def diagnostic(context, event, provider_status=None, error_code=None):
    # An explicit allowlist also covers legacy models with permissive request extras.
    context = context or {}
    safe = {key: context.get(key) for key in ("request_id", "model", "provider_api")}
    effort = context.get("reasoning_effort")
    safe["reasoning_effort"] = effort if isinstance(effort, str) and effort in {"none", "minimal", "low", "medium", "high", "xhigh", "max"} else None
    logger.info(json.dumps({**safe, "event": event, "provider": "azure" if settings.azure_endpoint else "litellm", "provider_status": provider_status, "error_code": error_code}))


async def check_status(response, context):
    diagnostic(context, "provider_response", response.status_code)
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        await response.aread()
        try:
            error = response.json().get("error") or {}
        except (ValueError, AttributeError):
            error = {}
        if not isinstance(error, dict):
            error = {}
        code = error.get("code") if isinstance(error, dict) else None
        safe_code = code if code in {"unsupported_value", "unsupported_parameter", "invalid_request_error", "model_not_found", "DeploymentNotFound"} else "provider_rejected"
        diagnostic(context, "provider_rejection", response.status_code, safe_code)
        message = str(error.get("message", "")) if isinstance(error, dict) else ""
        if context and context.get("model") in {"gpt-6-astra", "gpt-5.4", "gpt-5.6-sol"} and response.status_code == 400 and ("reasoning" in message.lower() or error.get("param") in {"reasoning.effort", "reasoning_effort"}):
            effort = context.get("reasoning_effort")
            raise ProviderGatewayError(f"Requested reasoning effort '{effort}' is unavailable for the configured {context['model']} deployment/API. Verify the Azure deployment version and capabilities.", code="provider_reasoning_unavailable", status_code=400) from exc
        raise ProviderGatewayError("Model provider rejected the request. Check model capabilities or contact support.") from exc


async def create_chat_completion(payload: dict[str, Any], *, context=None, responses=False) -> dict[str, Any]:
    api = "responses" if responses else "chat/completions"
    diagnostic(context, "provider_request")
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False) as client:
            response = await client.post(_chat_url(api), headers=_headers(), json=payload)
            await check_status(response, context)
        result = response.json()
        if responses:
            result = from_responses(result)
        if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
            raise ValueError("Malformed completion")
        return result
    except (httpx.HTTPError, ValueError) as exc:
        diagnostic(context, "provider_failed", error_code="transport_or_response_error")
        raise ProviderGatewayError("Model provider unavailable. Please try again later.") from exc


async def stream_chat_completion(payload: dict[str, Any], *, context=None, responses=False) -> AsyncIterator[bytes]:
    client = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False)
    diagnostic(context, "provider_request")
    try:
        request = client.build_request("POST", _chat_url("responses" if responses else "chat/completions"), headers=_headers(), json=payload)
        response = await client.send(request, stream=True)
        await check_status(response, context)
    except BaseException as exc:
        await client.aclose()
        if isinstance(exc, httpx.HTTPError):
            diagnostic(context, "provider_failed", error_code="transport_error")
            raise ProviderGatewayError("Model provider unavailable. Please try again later.") from exc
        raise

    async def raw():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    async def iterator():
        source = stream_to_chat(raw()) if responses else raw()
        try:
            async for chunk in source:
                yield chunk
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            diagnostic(context, "provider_stream_failed", error_code="invalid_stream")
            raise ProviderGatewayError("Model provider stream interrupted.") from exc
        finally:
            await source.aclose()

    return iterator()
