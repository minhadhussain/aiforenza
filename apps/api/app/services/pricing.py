from decimal import Decimal
from decimal import ROUND_HALF_UP

from app.models.catalog import CatalogModel
from app.models.usage import CustomerCharge
from app.models.usage import UsageMetrics


ONE_MILLION = Decimal("1000000")


def _decimal(value: str | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def calculate_customer_charge(model: CatalogModel, usage: UsageMetrics) -> CustomerCharge:
    input_component = (_decimal(model.customer_input_price_per_million) * Decimal(usage.input_tokens)) / ONE_MILLION
    output_component = (_decimal(model.customer_output_price_per_million) * Decimal(usage.output_tokens)) / ONE_MILLION
    cached_component = (_decimal(model.customer_cached_input_price_per_million) * Decimal(usage.cached_input_tokens)) / ONE_MILLION
    total_cents = int(((input_component + output_component + cached_component) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    return CustomerCharge(
        cents=max(total_cents, 0),
        input_component=input_component,
        output_component=output_component,
        cached_component=cached_component,
    )


def estimate_text_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0
