from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import settings


class LiteLLMProxyError(Exception):
    pass


def _base_url() -> str:
    return settings.litellm_url.rstrip("/")


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.litellm_master_key:
        headers["Authorization"] = f"Bearer {settings.litellm_master_key}"
    return headers


def _normalize_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return response.text or "LiteLLM request failed."

    if isinstance(payload, dict):
        if isinstance(payload.get("error"), dict):
            return payload["error"].get("message", "LiteLLM request failed.")
        return payload.get("message") or payload.get("detail") or "LiteLLM request failed."

    return "LiteLLM request failed."


async def create_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{_base_url()}/v1/chat/completions",
            headers=_headers(),
            json=payload,
        )

    if response.status_code >= 400:
        raise LiteLLMProxyError(_normalize_error(response))

    return response.json()


async def stream_chat_completion(payload: dict[str, Any]) -> AsyncIterator[bytes]:
    client = httpx.AsyncClient(timeout=None)
    request = client.build_request(
        "POST",
        f"{_base_url()}/v1/chat/completions",
        headers=_headers(),
        json=payload,
    )
    response = await client.send(request, stream=True)

    if response.status_code >= 400:
        message = _normalize_error(response)
        await response.aclose()
        await client.aclose()
        raise LiteLLMProxyError(message)

    async def iterator() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                if chunk:
                    yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return iterator()
