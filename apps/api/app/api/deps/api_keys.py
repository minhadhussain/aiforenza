from fastapi import Header
from fastapi import status

from app.core.errors import OpenAIAPIError
from app.services.api_keys import ApiKeyServiceError
from app.services.api_keys import authenticate_api_key
from app.services.api_keys import touch_api_key_last_used


async def get_current_api_key(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise OpenAIAPIError(
            "Invalid API key.",
            error_type="invalid_request_error",
            code="invalid_api_key",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    api_key = authorization.removeprefix("Bearer ").strip()
    if not api_key:
        raise OpenAIAPIError(
            "Invalid API key.",
            error_type="invalid_request_error",
            code="invalid_api_key",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    try:
        record = await authenticate_api_key(api_key)
    except ApiKeyServiceError as exc:
        raise OpenAIAPIError(
            str(exc),
            error_type="api_error",
            code="api_key_lookup_failed",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc

    if record is None:
        raise OpenAIAPIError(
            "Invalid API key.",
            error_type="invalid_request_error",
            code="invalid_api_key",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    await touch_api_key_last_used(record["id"])
    return record
