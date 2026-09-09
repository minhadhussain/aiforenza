from decimal import Decimal
from decimal import ROUND_CEILING

from app.models.catalog import CatalogModel
from app.models.pricing import RequestChargeBreakdown
from app.models.usage import UsageMetrics
from datetime import datetime, timezone


ONE_MILLION = Decimal("1000000")
ONE_HUNDRED = Decimal("100")


def _decimal(value: str | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0")
    result = Decimal(str(value))
    if not result.is_finite() or result < 0:
        raise ValueError("Prices must be finite and non-negative")
    return result


def _cents(amount: Decimal) -> int:
    # Integer-cent wallet: round each positive request total up, once, not per token.
    return int((amount * ONE_HUNDRED).quantize(Decimal("1"), rounding=ROUND_CEILING))


def resolve_customer_multiplier(model: CatalogModel) -> Decimal:
    discount = _decimal(model.discount_percent)
    if discount > 100:
        raise ValueError("Discount must be between zero and 100")
    multiplier = Decimal("1") - (discount / Decimal("100"))
    return multiplier if multiplier >= Decimal("0") else Decimal("0")


def is_pricing_available(model: CatalogModel) -> bool:
    return bool(model.enabled and model.pricing_verified and model.reference_price_source
                and model.reference_price_valid_until
                and model.reference_price_valid_until > datetime.now(timezone.utc)
                and model.input_price_per_million is not None
                and model.output_price_per_million is not None)


def resolve_model_rates(model: CatalogModel) -> dict[str, Decimal]:
    if model.input_price_per_million is None or model.output_price_per_million is None:
        raise ValueError("Reference pricing is not configured")
    reference = {
        "input": _decimal(model.input_price_per_million),
        "output": _decimal(model.output_price_per_million),
        "cached_input": _decimal(model.cached_input_price_per_million if model.cached_input_price_per_million is not None else model.input_price_per_million),
    }
    multiplier = resolve_customer_multiplier(model)
    return {**{f"reference_{name}": rate for name,rate in reference.items()},
            **{f"customer_{name}": rate * multiplier for name,rate in reference.items()}}


def calculate_pricing_breakdown(model: CatalogModel, usage: UsageMetrics, provider_cost_cents: int | None = None) -> RequestChargeBreakdown:
    rates = resolve_model_rates(model)
    reference_input_component = rates["reference_input"] * (usage.input_tokens-usage.cached_input_tokens) / ONE_MILLION
    reference_output_component = rates["reference_output"] * usage.output_tokens / ONE_MILLION
    reference_cached_component = rates["reference_cached_input"] * usage.cached_input_tokens / ONE_MILLION

    reference_total = reference_input_component + reference_output_component + reference_cached_component
    multiplier = resolve_customer_multiplier(model)

    customer_input_component = reference_input_component * multiplier
    customer_output_component = reference_output_component * multiplier
    customer_cached_component = reference_cached_component * multiplier
    customer_total = customer_input_component + customer_output_component + customer_cached_component

    reference_charge_cents = max(_cents(reference_total), 0)
    customer_charge_cents = max(_cents(customer_total), 0)
    customer_savings_cents = max(reference_charge_cents - customer_charge_cents, 0)

    if provider_cost_cents is None and model.provider_cost_source and model.provider_input_cost_per_million is not None and model.provider_output_cost_per_million is not None:
        cached_cost = model.provider_cached_input_cost_per_million
        if cached_cost is not None or usage.cached_input_tokens == 0:
            provider_cost_cents = _cents((model.provider_input_cost_per_million * (usage.input_tokens-usage.cached_input_tokens)
                + model.provider_output_cost_per_million * usage.output_tokens
                + (cached_cost or Decimal("0")) * usage.cached_input_tokens) / ONE_MILLION)

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
