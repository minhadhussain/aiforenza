from app.models.catalog import CatalogModel
from app.repositories.supabase_rest import rest_select


async def fetch_enabled_models() -> list[CatalogModel]:
    payload = await rest_select(
        path="/rest/v1/models",
        params={
            "enabled": "eq.true",
            "select": "id,slug,display_name,provider,provider_model_id,enabled,input_price_per_million,output_price_per_million,cached_input_price_per_million,discount_percent,customer_input_price_per_million,customer_output_price_per_million,customer_cached_input_price_per_million",
            "order": "display_name.asc",
        },
    )
    return [CatalogModel.model_validate(item) for item in payload]


async def fetch_model_by_slug(slug: str) -> CatalogModel | None:
    payload = await rest_select(
        path="/rest/v1/models",
        params={
            "slug": f"eq.{slug}",
            "enabled": "eq.true",
            "select": "id,slug,display_name,provider,provider_model_id,enabled,input_price_per_million,output_price_per_million,cached_input_price_per_million,discount_percent,customer_input_price_per_million,customer_output_price_per_million,customer_cached_input_price_per_million",
            "limit": "1",
        },
    )
    return CatalogModel.model_validate(payload[0]) if payload else None
