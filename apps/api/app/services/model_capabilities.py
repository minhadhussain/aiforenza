"""Model-scoped Chat compatibility, driven by the backend catalog."""

from app.core.errors import OpenAIAPIError
from app.models.catalog import CatalogModel
from app.models.openai import ChatCompletionRequest


def invalid_option(message: str, code: str = "unsupported_reasoning_effort"):
    return OpenAIAPIError(message, error_type="invalid_request_error", code=code, status_code=400)


def reasoning_effort(request: ChatCompletionRequest, model: CatalogModel) -> str | None:
    caps = model.capabilities
    if model.slug == "gpt-6-astra" and not caps.reasoning:
        raise OpenAIAPIError("Astra capabilities are not configured.", error_type="api_error", code="model_configuration_error", status_code=503)
    if not caps.reasoning:
        return None
    payload = request.model_dump(exclude_none=True)
    choices = [payload[key] for key in ("reasoning_effort", "reasoningEffort") if key in payload]
    if "reasoning" in payload:
        reasoning = payload["reasoning"]
        if not isinstance(reasoning, dict) or set(reasoning) - {"effort", "summary"}:
            raise invalid_option("Only reasoning.effort is supported by this Chat compatibility endpoint.")
        if "effort" in reasoning:
            choices.append(reasoning["effort"])
    if any(not isinstance(value, str) or value not in caps.reasoning_efforts for value in choices):
        raise invalid_option("Supported reasoning efforts: " + ", ".join(caps.reasoning_efforts) + ".")
    if len(set(choices)) > 1:
        raise invalid_option("Conflicting reasoning effort options.", "conflicting_reasoning_effort")
    effort = choices[0] if choices else caps.default_reasoning_effort
    if effort not in caps.reasoning_efforts:
        raise OpenAIAPIError("Model reasoning default is not configured.", error_type="api_error", code="model_configuration_error", status_code=503)
    return effort


def normalize_model_payload(request: ChatCompletionRequest, model: CatalogModel) -> dict:
    payload = request.model_dump(exclude_none=True)
    effort = reasoning_effort(request, model)
    if effort is None:
        return payload
    # Chat controls only. SDK/Responses-only extras never reach Azure blindly.
    allowed = {"model", "messages", "max_tokens", "max_completion_tokens", "stream", "stream_options", "tools", "tool_choice", "parallel_tool_calls", "response_format", "service_tier", "n"}
    if model.capabilities.temperature:
        allowed.add("temperature")
    if model.capabilities.top_p:
        allowed.add("top_p")
    normalized = {key: value for key, value in payload.items() if key in allowed}
    normalized["reasoning_effort"] = effort
    if "functions" in payload or "function_call" in payload:
        raise invalid_option("Use tools and tool_choice for function calls.", "unsupported_tool_format")
    tools = normalized.get("tools", [])
    if not isinstance(tools, list) or any(not isinstance(tool, dict) or tool.get("type") != "function" or not isinstance(tool.get("function"), dict) for tool in tools):
        raise invalid_option("Only function tools are supported.", "unsupported_tool_format")
    # Preserve content, tool call IDs/results and names; omit opaque SDK metadata.
    message_fields = {"role", "content", "name", "tool_calls", "tool_call_id"}
    normalized["messages"] = [{k: v for k, v in message.items() if k in message_fields} for message in payload["messages"]]
    return normalized


def uses_responses(payload: dict, model: CatalogModel) -> bool:
    caps = model.capabilities
    return payload.get("reasoning_effort") in caps.responses_efforts or (
        caps.responses_for_tools and payload.get("reasoning_effort") != "none" and (
            bool(payload.get("tools")) or any(message.get("role") == "tool" or message.get("tool_calls") for message in payload["messages"])
        )
    )
