from decimal import Decimal
from decimal import ROUND_HALF_UP

from app.models.catalog import CatalogModel
from app.models.pricing import RequestChargeBreakdown
from app.models.usage import UsageMetrics


ONE_MILLION = Decimal("1000000")
ONE_HUNDRED = Decimal("100")


def _decimal(value: str | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def _cents(amount: Decimal) -> int:
    return int((amount * ONE_HUNDRED).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def resolve_customer_multiplier(model: CatalogModel) -> Decimal:
    discount = _decimal(model.discount_percent)
    multiplier = Decimal("1") - (discount / Decimal("100"))
    return multiplier if multiplier >= Decimal("0") else Decimal("0")


def calculate_pricing_breakdown(model: CatalogModel, usage: UsageMetrics, provider_cost_cents: int | None = None) -> RequestChargeBreakdown:
    reference_input_component = (_decimal(model.input_price_per_million) * Decimal(usage.input_tokens)) / ONE_MILLION
    reference_output_component = (_decimal(model.output_price_per_million) * Decimal(usage.output_tokens)) / ONE_MILLION
    reference_cached_component = (_decimal(model.cached_input_price_per_million) * Decimal(usage.cached_input_tokens)) / ONE_MILLION

    reference_total = reference_input_component + reference_output_component + reference_cached_component
    multiplier = resolve_customer_multiplier(model)

    customer_input_component = reference_input_component * multiplier
    customer_output_component = reference_output_component * multiplier
    customer_cached_component = reference_cached_component * multiplier
    customer_total = customer_input_component + customer_output_component + customer_cached_component

    reference_charge_cents = max(_cents(reference_total), 0)
    customer_charge_cents = max(_cents(customer_total), 0)
    customer_savings_cents = max(reference_charge_cents - customer_charge_cents, 0)

    return RequestChargeBreakdown(
        reference_charge_cents=reference_charge_cents,
        customer_charge_cents=customer_charge_cents,
        customer_savings_cents=customer_savings_cents,
        provider_cost_cents=provider_cost_cents,
        reference_input_component=reference_input_component,
        reference_output_component=reference_output_component,
        reference_cached_component=reference_cached_component,
        customer_input_component=customer_input_component,
        customer_output_component=customer_output_component,
        customer_cached_component=customer_cached_component,
    )


def estimate_customer_charge_cents(request_max_usage: UsageMetrics, model: CatalogModel) -> int:
    return calculate_pricing_breakdown(model, request_max_usage).customer_charge_cents


def estimate_text_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4) if text else 0
