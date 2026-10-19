import pytest

from app.models.openai import ChatCompletionRequest
from app.services.chat_completions import build_provider_payload
from app.models.catalog import CatalogModel
from test_astra_catalog import catalog_row


@pytest.mark.parametrize("stream", [False, True])
@pytest.mark.parametrize("slug", ["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra"])
def test_opencode_summary_option_not_forwarded_to_chat_api(stream, slug):
    request = ChatCompletionRequest(
        model=slug,
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
        request, CatalogModel.model_validate(catalog_row(slug)), "req_test"
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
        request, CatalogModel.model_validate(catalog_row("gpt-5.4")), "req_test"
    )
    assert payload == {**request.model_dump(exclude_none=True), "reasoning_effort": "none"}


@pytest.mark.parametrize(
    "slug", ["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6", "other-model"]
)
def test_alias_precedence_and_other_models(slug):
    request = ChatCompletionRequest(
        model=slug,
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=1000,
        max_completion_tokens=500,
    )
    payload = build_provider_payload(
        request, CatalogModel.model_validate(catalog_row(slug)), "req_test"
    )
    assert payload["max_completion_tokens"] == 500
    if slug in {"gpt-5.4", "gpt-5.6-sol", "gpt-6-astra"}:
        assert "max_tokens" not in payload
    else:
        assert payload["max_tokens"] == 1000


@pytest.mark.parametrize("slug", ["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6"])
def test_upstream_routing_credentials_and_unmetered_extras_never_leave_the_gateway(slug):
    unsafe = {
        "api_key": "PRIVATE_CLIENT_SECRET", "api_base": "https://untrusted.invalid",
        "base_url": "https://untrusted.invalid", "custom_llm_provider": "unapproved",
        "headers": {"Authorization": "PRIVATE_CLIENT_SECRET"},
        "web_search_options": {"search_context_size": "high"}, "modalities": ["audio"],
        "audio": {"voice": "alloy", "format": "wav"}, "previous_response_id": "unbilled-history",
        "max_output_tokens": 99999999, "billing_source": "PROMOTIONAL", "store": True,
    }
    request = ChatCompletionRequest(
        model=slug, messages=[{"role": "user", "content": "Hello", "audio": {"id": "unbilled-audio"}, "opaque": "PRIVATE_MESSAGE_METADATA"}],
        **unsafe,
    )
    model = CatalogModel.model_validate(catalog_row(slug))
    model.provider_model_id = "server-approved-deployment"
    payload = build_provider_payload(request, model, "req_fixture")
    assert not (set(unsafe) & payload.keys())
    assert payload["model"] == "server-approved-deployment"
    assert payload["messages"] == [{"role": "user", "content": "Hello"}]
    assert payload["max_completion_tokens"] == 1024


@pytest.mark.parametrize("slug", ["gpt-5.4", "gpt-5.6-sol", "gpt-6-astra", "grok-4.6"])
@pytest.mark.parametrize("tool", [{"type": "web_search"}, {"type": "code_interpreter"}, {"type": "computer_use"}])
def test_unmetered_hosted_tools_are_rejected_for_every_model(slug, tool):
    from app.core.errors import OpenAIAPIError

    request = ChatCompletionRequest(model=slug, messages=[{"role": "user", "content": "Hello"}], tools=[tool])
    with pytest.raises(OpenAIAPIError) as error:
        build_provider_payload(request, CatalogModel.model_validate(catalog_row(slug)), "req_fixture")
    assert error.value.code == "unsupported_tool_format"
