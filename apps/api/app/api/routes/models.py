from fastapi import APIRouter, Depends

from app.api.deps.api_keys import get_current_api_key
from app.services.models import list_models
from app.services.models import serialize_openai_models


router = APIRouter()


@router.get("/models")
async def get_models(_: dict = Depends(get_current_api_key)) -> dict:
    return serialize_openai_models(await list_models())
