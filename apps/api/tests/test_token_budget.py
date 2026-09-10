import pytest
from app.core.errors import OpenAIAPIError
from app.models.openai import ChatCompletionRequest
from app.services import token_budget
from app.services.usage_records import preflight_spending_details
from test_pricing import build_model


def request(text, **kwargs):
    return ChatCompletionRequest(
        model="gpt-6-astra",
        messages=[{"role": "user", "content": text}],
        max_tokens=32,
        **kwargs,
    )


def test_long_text_not_confused_with_utf8_byte_limit():
    model = build_model()
    req = request("def calculate(value): return value + 1\n" * 6000)
    estimate, capacity, method = token_budget.input_budgets(req)
    assert capacity > 190000 and estimate < 190000
    result = preflight_spending_details(req, model)
    assert result["reservation_input_budget"] == capacity
    assert result["input_token_estimate"] == estimate


@pytest.mark.parametrize(
    "text", ["hello", "你好世界" * 100, "😀🌍" * 100, "<|endoftext|>", "e\u0301" * 100]
)
def test_unicode_special_strings_and_capacity(text):
    estimate, capacity, method = token_budget.input_budgets(request(text))
    assert 0 < estimate <= capacity
    assert method == "dual_encoding_margin"


def test_tool_schemas_and_results_included():
    small = token_budget.input_budgets(request("Hi"))[0]
    large = token_budget.input_budgets(
        request(
            "Hi",
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": "tool",
                        "description": "documentation " * 1000,
                    },
                }
            ],
        )
    )[0]
    assert large > small


def test_unknown_model_and_encoding_failure_use_conservative_fallback(monkeypatch):
    req = request("Hi")
    monkeypatch.setattr(
        token_budget,
        "encodings",
        lambda: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    estimate, capacity, method = token_budget.input_budgets(req)
    assert estimate == capacity and method == "utf8_fallback"
    req.model = "unknown"
    assert token_budget.input_budgets(req)[2] == "utf8_upper_bound"


def test_exact_limits_and_diagnostics(monkeypatch):
    model = build_model()
    from app.services import usage_records

    monkeypatch.setattr(
        usage_records, "input_budgets", lambda _: (190000, 500000, "fixture")
    )
    req = request("PRIVATE PROMPT")
    req.max_tokens = 32768
    assert preflight_spending_details(req, model)["reservation_input_budget"] == 500000
    req.max_tokens = 32769
    with pytest.raises(OpenAIAPIError) as exc:
        preflight_spending_details(req, model)
    assert "32769" in exc.value.message and "32768" in exc.value.message
    assert "PRIVATE" not in exc.value.message
    req.max_tokens = 32
    monkeypatch.setattr(
        usage_records, "input_budgets", lambda _: (190001, 500000, "fixture")
    )
    with pytest.raises(OpenAIAPIError, match="estimated input 190001"):
        preflight_spending_details(req, model)
