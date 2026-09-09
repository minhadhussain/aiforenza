from app.models.catalog import CatalogModel
from app.repositories.supabase_rest import rest_select
from app.services.pricing import is_pricing_available

MODEL_FIELDS = "id,slug,display_name,provider,provider_model_id,enabled,input_price_per_million,output_price_per_million,cached_input_price_per_million,discount_percent,pricing_verified,reference_price_source,reference_price_checked_at,reference_price_valid_until,pricing_max_input_tokens,pricing_max_output_tokens,provider_input_cost_per_million,provider_output_cost_per_million,provider_cached_input_cost_per_million,provider_cost_source"


async def fetch_enabled_models() -> list[CatalogModel]:
    payload = await rest_select(
        path="/rest/v1/models",
        params={
            "enabled": "eq.true",
            "select": MODEL_FIELDS,
            "order": "display_name.asc",
        },
    )
    models = [CatalogModel.model_validate(item) for item in payload]
    return [model for model in models if is_pricing_available(model)]


async def fetch_model_by_slug(slug: str) -> CatalogModel | None:
    payload = await rest_select(
        path="/rest/v1/models",
        params={
            "slug": f"eq.{slug}",
            "enabled": "eq.true",
            "select": MODEL_FIELDS,
            "limit": "1",
        },
    )
    model = CatalogModel.model_validate(payload[0]) if payload else None
    return model if model and is_pricing_available(model) else None
