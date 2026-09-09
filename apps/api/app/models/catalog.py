from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field
from pydantic import ConfigDict


class CatalogModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    display_name: str
    provider: str
    provider_model_id: str
    enabled: bool
    input_price_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    output_price_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    cached_input_price_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    discount_percent: Decimal = Field(default=Decimal("40"), ge=0, le=100, allow_inf_nan=False)
    # Compatibility fields only; the pricing service derives the authoritative rates.
    customer_input_price_per_million: Decimal | None = None
    customer_output_price_per_million: Decimal | None = None
    customer_cached_input_price_per_million: Decimal | None = None
    pricing_verified: bool = False
    reference_price_source: str | None = None
    reference_price_checked_at: datetime | None = None
    reference_price_valid_until: datetime | None = None
    pricing_max_input_tokens: int = Field(default=190000, gt=0)
    pricing_max_output_tokens: int = Field(default=32768, gt=0)
    provider_input_cost_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    provider_output_cost_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    provider_cached_input_cost_per_million: Decimal | None = Field(default=None, ge=0, allow_inf_nan=False)
    provider_cost_source: str | None = None
