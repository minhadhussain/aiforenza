from types import SimpleNamespace

import pytest

from app.models.openai import ChatCompletionRequest
from app.services.chat_completions import build_provider_payload


@pytest.mark.parametrize("stream", [False, True])
def test_opencode_summary_option_not_forwarded_to_chat_api(stream):
    request = ChatCompletionRequest(
        model="gpt-5.4",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=32000,
        reasoningSummary="auto",
        reasoning_effort="medium",
        verbosity="medium",
        stream=stream,
        tools=[{"type": "function", "function": {"name": "example"}}],
    )
    before = request.model_dump()
    payload = build_provider_payload(
        request, SimpleNamespace(provider_model_id="gpt-5.4"), "req_test"
    )
    assert "reasoningSummary" not in payload
    assert payload["reasoning_effort"] == "medium"
    assert payload["max_completion_tokens"] == 32000
    assert "max_tokens" not in payload
    assert payload["tools"] == before["tools"]
    assert request.model_dump() == before
    if stream:
        assert payload["stream_options"] == {"include_usage": True}


def test_standard_chat_request_remains_unchanged():
    request = ChatCompletionRequest(
        model="gpt-5.4",
        messages=[{"role": "user", "content": "Hello"}],
        max_completion_tokens=32000,
    )
    payload = build_provider_payload(
        request, SimpleNamespace(provider_model_id="gpt-5.4"), "req_test"
    )
    assert payload == request.model_dump(exclude_none=True)


@pytest.mark.parametrize("slug", ["gpt-5.4", "other-model"])
def test_alias_precedence_and_other_models(slug):
    request = ChatCompletionRequest(
        model=slug,
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1000,
        max_completion_tokens=500,
    )
    payload = build_provider_payload(
        request, SimpleNamespace(provider_model_id=slug), "req_test"
    )
    assert payload["max_completion_tokens"] == 500
    if slug == "gpt-5.4":
        assert "max_tokens" not in payload
    else:
        assert payload["max_tokens"] == 1000
