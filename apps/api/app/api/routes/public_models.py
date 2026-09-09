from fastapi import APIRouter, HTTPException, status

from app.repositories.supabase_rest import SupabaseRepositoryError
from app.services.models import list_models
from app.services.models import ModelCatalogError
from app.services.models import serialize_dashboard_models


router = APIRouter()


@router.get("/public/models")
async def get_public_models() -> dict:
    try:
        models = await list_models()
    except (ModelCatalogError, SupabaseRepositoryError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Model catalog temporarily unavailable.") from exc

    return {"data": serialize_dashboard_models(models)}
