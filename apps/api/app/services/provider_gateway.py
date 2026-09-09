from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import urlsplit

import httpx

from app.core.config import settings


class ProviderGatewayError(Exception):
    """Safe public error; never carries upstream bodies or credentials."""


def _chat_url() -> str:
    if settings.azure_endpoint:
        endpoint = settings.azure_endpoint.rstrip("/")
        parsed = urlsplit(endpoint)
        if not settings.azure_api_key or parsed.scheme != "https" or parsed.query or not parsed.path.endswith("/openai/v1"):
            raise ProviderGatewayError("Model provider is not configured correctly.")
        return f"{endpoint}/chat/completions"
    return f"{settings.litellm_url.rstrip('/')}/v1/chat/completions"


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if settings.azure_endpoint:
        headers["api-key"] = settings.azure_api_key
    elif settings.litellm_master_key:
        headers["Authorization"] = f"Bearer {settings.litellm_master_key}"
    return headers


async def create_chat_completion(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False) as client:
            response = await client.post(_chat_url(), headers=_headers(), json=payload)
        response.raise_for_status()
        result = response.json()
        if not isinstance(result, dict) or not isinstance(result.get("choices"), list):
            raise ValueError("Malformed completion")
        return result
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderGatewayError("Model provider unavailable. Please try again later.") from exc


async def stream_chat_completion(payload: dict[str, Any]) -> AsyncIterator[bytes]:
    client = httpx.AsyncClient(timeout=httpx.Timeout(120, connect=10), follow_redirects=False)
    try:
        request = client.build_request("POST", _chat_url(), headers=_headers(), json=payload)
        response = await client.send(request, stream=True)
        response.raise_for_status()
    except BaseException as exc:
        await client.aclose()
        if isinstance(exc, httpx.HTTPError):
            raise ProviderGatewayError("Model provider unavailable. Please try again later.") from exc
        raise

    async def iterator() -> AsyncIterator[bytes]:
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        except httpx.HTTPError as exc:
            raise ProviderGatewayError("Model provider stream interrupted.") from exc
        finally:
            await response.aclose()
            await client.aclose()

    return iterator()
