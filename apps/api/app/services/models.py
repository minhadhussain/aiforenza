from app.models.catalog import CatalogModel
from app.repositories.models import fetch_enabled_models
from app.repositories.models import fetch_model_by_slug
from app.repositories.supabase_rest import SupabaseRepositoryError


class ModelCatalogError(Exception):
    pass


async def list_models() -> list[CatalogModel]:
    try:
        return await fetch_enabled_models()
    except SupabaseRepositoryError as exc:
        raise ModelCatalogError(str(exc)) from exc


async def get_model_by_slug(slug: str) -> CatalogModel | None:
    try:
        return await fetch_model_by_slug(slug)
    except SupabaseRepositoryError as exc:
        raise ModelCatalogError(str(exc)) from exc


def serialize_openai_models(models: list[CatalogModel]) -> dict:
    return {
        "object": "list",
        "data": [
            {
                "id": model.slug,
                "object": "model",
                "owned_by": "your-platform",
            }
            for model in models
        ],
    }
