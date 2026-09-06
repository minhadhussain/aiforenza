from fastapi import APIRouter, Depends

from app.api.deps.api_keys import get_current_api_key


router = APIRouter()


@router.get("/models")
async def get_models(_: dict = Depends(get_current_api_key)) -> dict:
    return {"object": "list", "data": []}
