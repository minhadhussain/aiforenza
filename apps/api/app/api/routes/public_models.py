from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse
import httpx

from app.core.config import settings
from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services.models import list_models
from app.services.models import ModelCatalogError
from app.services.models import serialize_dashboard_models
from app.services.opencode_config import build_opencode_config


router = APIRouter()


@router.get("/public/opencode-config")
async def get_opencode_config() -> JSONResponse:
    """Public, key-free configuration: the same enabled catalog as /v1/models."""
    try:
        models = await list_models()
        config = build_opencode_config(
            models,
            settings.public_api_base_url,
            production=settings.api_env.lower() not in {"development", "test", "local"},
        )
    except (ModelCatalogError, SupabaseRepositoryError, httpx.HTTPError, ValueError):
        raise HTTPException(status_code=503, detail="OpenCode configuration unavailable. Check the model catalog and public API base URL.") from None
    return JSONResponse(config, headers={"Cache-Control": "no-store", "Content-Disposition": 'attachment; filename="opencode.json"'})


@router.get("/public/models")
async def get_public_models() -> dict:
    try:
        models = await list_models()
    except (ModelCatalogError, SupabaseRepositoryError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model catalog temporarily unavailable.") from exc

    return {"data": serialize_dashboard_models(models)}
