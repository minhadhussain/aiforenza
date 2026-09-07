from pydantic import BaseModel
from pydantic import ConfigDict


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    display_name: str
    provider: str
    provider_model_id: str
    enabled: bool
    input_price_per_million: str | int | float
    output_price_per_million: str | int | float
    cached_input_price_per_million: str | int | float | None = None
    customer_input_price_per_million: str | int | float
    customer_output_price_per_million: str | int | float
    customer_cached_input_price_per_million: str | int | float | None = None
