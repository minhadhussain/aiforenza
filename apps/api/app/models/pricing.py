from decimal import Decimal

from pydantic import BaseModel


class RequestChargeBreakdown(BaseModel):
    reference_charge_cents: int
    customer_charge_cents: int
    customer_savings_cents: int
    provider_cost_cents: int | None = None
    reference_input_component: Decimal
    reference_output_component: Decimal
    reference_cached_component: Decimal
    customer_input_component: Decimal
    customer_output_component: Decimal
    customer_cached_component: Decimal
