from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings


class ProviderGatewayError(Exception):
    pass


def _base_url() -> str:
    if settings.azure_endpoint and settings.azure_api_key:
        return settings.azure_endpoint.rstrip("/")
    return settings.litellm_url.rstrip("/")


def _headers() -> dict[str, str]:
    if settings.azure_endpoint and settings.azure_api_key:
        return {
            "Content-Type": "application/json",
            "api-key": settings.azure_api_key,
        }

    headers = {"Content-Type": "application/json"}
    if settings.litellm_master_key:
        headers["Authorization"] = f"Bearer {settings.litellm_master_key}"
    return headers


def _chat_url() -> str:
    base = _base_url()
    if settings.azure_endpoint and settings.azure_api_key:
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _normalize_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "Provider request failed."

    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            return payload["error"].get("message", "Provider request failed.")
        return payload.get("message") or payload.get("detail") or "Provider request failed."

    return "Provider request failed."


async def create_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            _chat_url(),
            headers=_headers(),
            json=payload,
        )

    if response.status_code >= 400:
        raise ProviderGatewayError(_normalize_error(response))

    return response.json()


async def stream_chat_completion(payload: dict[str, Any]) -> AsyncIterator[bytes]:
    client = httpx.AsyncClient(timeout=None)
    request = client.build_request(
        "POST",
        _chat_url(),
        headers=_headers(),
        json=payload,
    )
    response = await client.send(request, stream=True)

    if response.status_code >= 400:
        message = _normalize_error(response)
        await response.aclose()
        await client.aclose()
        raise ProviderGatewayError(message)

    async def iterator() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return iterator()
