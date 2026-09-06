from fastapi import Header, HTTPException, status

from app.services.api_keys import ApiKeyServiceError
from app.services.api_keys import authenticate_api_key
from app.services.api_keys import touch_api_key_last_used


async def get_current_api_key(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    api_key = authorization.removeprefix("Bearer ").strip()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    try:
        record = await authenticate_api_key(api_key)
    except ApiKeyServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )

    await touch_api_key_last_used(record["id"])
    return record
