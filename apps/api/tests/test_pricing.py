from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.models.openai import ChatMessage
from app.models.usage import UsageMetrics
from app.services.pricing import calculate_pricing_breakdown
from app.services.pricing import resolve_customer_multiplier
from app.services.usage_records import estimate_preflight_charge_cents
from app.services.usage_records import extract_usage_metrics


def build_model() -> CatalogModel:
    return CatalogModel(
        id="model-1",
        slug="gpt-5.6-luna",
        display_name="GPT-5.6 Luna",
        provider="azure",
        provider_model_id="gpt-5.6-luna",
        enabled=True,
        input_price_per_million=10,
        output_price_per_million=20,
        cached_input_price_per_million=5,
        discount_percent=40,
        customer_input_price_per_million=6,
        customer_output_price_per_million=12,
        customer_cached_input_price_per_million=3,
    )


def test_resolve_customer_multiplier_uses_40_percent_discount() -> None:
    assert str(resolve_customer_multiplier(build_model())) == "0.6"


def test_calculate_pricing_breakdown_applies_40_percent_discount() -> None:
    breakdown = calculate_pricing_breakdown(
        build_model(),
        UsageMetrics(input_tokens=500000, output_tokens=250000, cached_input_tokens=100000),
    )

    assert breakdown.reference_charge_cents == 950
    assert breakdown.customer_charge_cents == 570
    assert breakdown.customer_savings_cents == 380


def test_extract_usage_metrics_prefers_provider_usage() -> None:
    usage = extract_usage_metrics(
        {
            "usage": {
                "prompt_tokens": 120,
                "completion_tokens": 45,
                "prompt_tokens_details": {"cached_tokens": 8},
            }
        }
    )

    assert usage.input_tokens == 120
    assert usage.output_tokens == 45
    assert usage.cached_input_tokens == 8


def test_estimate_preflight_charge_uses_request_budget() -> None:
    request = ChatCompletionRequest(
        model="gpt-5.6-luna",
        messages=[ChatMessage(role="user", content="hello world")],
        max_completion_tokens=200,
    )

    cents = estimate_preflight_charge_cents(request, build_model())
    assert cents >= 0


def test_ten_dollar_wallet_example_discount_semantics() -> None:
    model = CatalogModel(
        id="model-2",
        slug="gpt-5.6-sol",
        display_name="GPT-5.6 Sol",
        provider="azure",
        provider_model_id="gpt-5.6-sol",
        enabled=True,
        input_price_per_million=1000000,
        output_price_per_million=1000000,
        cached_input_price_per_million=0,
        discount_percent=40,
        customer_input_price_per_million=600000,
        customer_output_price_per_million=600000,
        customer_cached_input_price_per_million=0,
    )

    breakdown = calculate_pricing_breakdown(
        model,
        UsageMetrics(input_tokens=1, output_tokens=1, cached_input_tokens=0),
    )

    assert breakdown.reference_charge_cents == 200
    assert breakdown.customer_charge_cents == 120
    assert breakdown.customer_savings_cents == 80
