from app.models.catalog import CatalogModel
from app.services.pricing import resolve_model_rates
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
            **{f"{name}_price_per_million": str(rate) for name,rate in resolve_model_rates(model).items()},
            "discount_percent": str(model.discount_percent),
            "pricing_basis": "Standard text benchmark; USD per million tokens",
            "reference_price_source": getattr(model, "reference_price_source", None),
            "pricing_max_input_tokens": getattr(model, "pricing_max_input_tokens", 190000),
            "pricing_max_output_tokens": getattr(model, "pricing_max_output_tokens", 32768),
        }
        for model in models
    ]
