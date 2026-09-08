from app.models.catalog import CatalogModel
from app.services.pricing import resolve_customer_multiplier
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


def serialize_dashboard_models(models: list[CatalogModel]) -> list[dict]:
    return [
        {
            "id": model.id,
            "slug": model.slug,
            "display_name": model.display_name,
            "provider": model.provider,
            "reference_input_price_per_million": model.input_price_per_million,
            "reference_output_price_per_million": model.output_price_per_million,
            "reference_cached_input_price_per_million": model.cached_input_price_per_million,
            "discount_percent": model.discount_percent,
            "customer_input_price_per_million": float(float(model.input_price_per_million) * float(resolve_customer_multiplier(model))),
            "customer_output_price_per_million": float(float(model.output_price_per_million) * float(resolve_customer_multiplier(model))),
            "customer_cached_input_price_per_million": float(float(model.cached_input_price_per_million or 0) * float(resolve_customer_multiplier(model))),
        }
        for model in models
    ]
