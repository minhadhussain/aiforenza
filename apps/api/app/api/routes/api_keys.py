from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

from app.api.deps.auth import get_current_dashboard_user
from app.services.api_keys import ApiKeyServiceError
from app.services.api_keys import create_api_key_record
from app.services.api_keys import list_api_keys
from app.services.api_keys import revoke_api_key
from app.services.observability import capture_event


router = APIRouter()


class CreateApiKeyRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=80)


@router.get("/api-keys")
async def get_api_keys(user: dict = Depends(get_current_dashboard_user)) -> dict:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authenticated user is missing an id.")

    try:
        keys = await list_api_keys(user_id)
    except ApiKeyServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return {"data": keys}


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def post_api_key(payload: CreateApiKeyRequest, user: dict = Depends(get_current_dashboard_user)) -> dict:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authenticated user is missing an id.")

    try:
        result = await create_api_key_record(user_id, payload.name.strip())
    except ApiKeyServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    record = result["record"]
    capture_event(user_id, "api_key_created", {"api_key_id": record["id"], "name": record["name"]})
    return {
        "id": record["id"],
        "name": record["name"],
        "key_prefix": record["key_prefix"],
        "created_at": record["created_at"],
        "plaintext_key": result["plaintext_key"],
    }


@router.post("/api-keys/{key_id}/revoke")
async def post_api_key_revoke(key_id: UUID, user: dict = Depends(get_current_dashboard_user)) -> dict:
    user_id = user.get("id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Authenticated user is missing an id.")

    try:
        record = await revoke_api_key(user_id, str(key_id))
    except ApiKeyServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found.")

    capture_event(user_id, "api_key_revoked", {"api_key_id": record["id"]})

    return {"data": record}
