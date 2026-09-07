from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest
from app.models.openai import ChatMessage
from app.models.usage import UsageMetrics
from app.services.pricing import calculate_customer_charge
from app.services.usage_records import estimate_preflight_charge_cents
from app.services.usage_records import extract_usage_metrics


def build_model() -> CatalogModel:
    return CatalogModel(
        id="model-1",
        slug="gpt-5.6-luna",
        display_name="GPT-5.6 Luna",
        provider="azure",
        provider_model_id="azure/gpt-5.6-luna",
        enabled=True,
        input_price_per_million=1,
        output_price_per_million=2,
        cached_input_price_per_million=0.5,
        customer_input_price_per_million=2,
        customer_output_price_per_million=4,
        customer_cached_input_price_per_million=1,
    )


def test_calculate_customer_charge_uses_customer_prices() -> None:
    charge = calculate_customer_charge(
        build_model(),
        UsageMetrics(input_tokens=500000, output_tokens=250000, cached_input_tokens=100000),
    )

    assert charge.cents == 210


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
