"""Astra's provider-only Responses bridge; public API stays Chat Completions.

Stateless text/function-tool subset. Opaque/private reasoning items are neither
exposed to clients nor retained. Actual usage includes all reasoning output tokens.
"""

import json

from app.core.errors import OpenAIAPIError


def compatibility_error(message="Unsupported Astra tool conversation."):
    return OpenAIAPIError(message, error_type="invalid_request_error", code="unsupported_tool_format", status_code=400)


def to_responses(payload: dict) -> dict:
    if "functions" in payload or "function_call" in payload:
        raise compatibility_error("Use tools and tool_choice for reasoning requests that require Responses transport.")
    inputs = []
    for message in payload["messages"]:
        role = message["role"]
        if role == "tool":
            if not message.get("tool_call_id") or not isinstance(message.get("content"), str):
                raise compatibility_error()
            inputs.append({"type": "function_call_output", "call_id": message["tool_call_id"], "output": message["content"]})
            continue
        if role not in {"system", "developer", "user", "assistant"}:
            raise compatibility_error()
        content = message.get("content")
        if content is not None:
            if not isinstance(content, str):
                raise compatibility_error("Only text content is supported for metered requests.")
            inputs.append({"role": role, "content": content})
        for call in message.get("tool_calls", []):
            function = call.get("function", {})
            if role != "assistant" or call.get("type") != "function" or not call.get("id") or not isinstance(function.get("name"), str) or not isinstance(function.get("arguments"), str):
                raise compatibility_error()
            inputs.append({"type": "function_call", "call_id": call["id"], "name": function["name"], "arguments": function["arguments"]})
    result = {"model": payload["model"], "input": inputs, "max_output_tokens": payload["max_completion_tokens"], "stream": payload.get("stream", False), "store": False}
    if "reasoning_effort" in payload:
        result["reasoning"] = {"effort": payload["reasoning_effort"]}
    if payload.get("tools"):
        result["tools"] = []
        for tool in payload["tools"]:
            function = tool["function"]
            if not isinstance(function.get("name"), str):
                raise compatibility_error()
            result["tools"].append({"type": "function", **{k: v for k, v in function.items() if k in {"name", "description", "parameters", "strict"}}})
    choice = payload.get("tool_choice")
    if choice is not None:
        if isinstance(choice, str) and choice in {"auto", "none", "required"}:
            result["tool_choice"] = choice
        elif isinstance(choice, dict) and choice.get("type") == "function" and isinstance(choice.get("function", {}).get("name"), str):
            result["tool_choice"] = {"type": "function", "name": choice["function"]["name"]}
        else:
            raise compatibility_error()
    for key in ("parallel_tool_calls", "service_tier"):
        if key in payload:
            result[key] = payload[key]
    fmt = payload.get("response_format")
    if fmt is not None:
        if not isinstance(fmt, dict) or fmt.get("type") not in {"text", "json_object", "json_schema"}:
            raise compatibility_error("Unsupported response_format.")
        result["text"] = {"format": {"type": fmt["type"], **(fmt.get("json_schema", {}) if fmt["type"] == "json_schema" else {})}}
    return result


def chat_usage(usage):
    if not isinstance(usage, dict):
        return None
    # No estimates/fallback totals. The existing strict usage validator checks these.
    return {"prompt_tokens": usage.get("input_tokens"), "completion_tokens": usage.get("output_tokens"), "total_tokens": usage.get("total_tokens"), "prompt_tokens_details": {"cached_tokens": (usage.get("input_tokens_details") or {}).get("cached_tokens", 0)}, "completion_tokens_details": {"reasoning_tokens": (usage.get("output_tokens_details") or {}).get("reasoning_tokens", 0)}}


def from_responses(response: dict) -> dict:
    if response.get("status") not in {"completed", "incomplete"} or response.get("error"):
        raise ValueError("Unsuccessful provider response")
    if response.get("status") == "incomplete" and (response.get("incomplete_details") or {}).get("reason") != "max_output_tokens":
        raise ValueError("Unsettleable provider response")
    text, calls, refusal = [], [], []
    for item in response.get("output", []):
        if item.get("type") == "message":
            for part in item.get("content", []):
                if part.get("type") == "output_text":
                    text.append(part["text"])
                elif part.get("type") == "refusal":
                    refusal.append(part["refusal"])
        elif item.get("type") == "function_call":
            calls.append({"id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": item["arguments"]}})
    message = {"role": "assistant", "content": "".join(text) or None}
    if calls:
        message["tool_calls"] = calls
    if refusal:
        message["refusal"] = "".join(refusal)
    return {"id": response.get("id"), "object": "chat.completion", "created": response.get("created_at"), "model": response.get("model"), "choices": [{"index": 0, "message": message, "finish_reason": "length" if response["status"] == "incomplete" else "tool_calls" if calls else "stop"}], "usage": chat_usage(response.get("usage"))}


async def stream_to_chat(source):
    buffer = b""
    calls = {}
    done = False
    identity = {"object": "chat.completion.chunk"}

    def frame(delta, finish=None, usage=None):
        value = {**identity, "choices": [{"index": 0, "delta": delta, "finish_reason": finish}]}
        if usage is not None:
            value["usage"] = usage
        return ("data: " + json.dumps(value) + "\n\n").encode()

    try:
        async for chunk in source:
            buffer += chunk
            if len(buffer) > 2_000_000:
                raise ValueError("Provider stream frame too large")
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line.startswith(b"data:"):
                    continue
                event = json.loads(line[5:].strip())
                kind = event.get("type")
                if kind == "response.created":
                    response = event["response"]
                    identity.update(id=response["id"], created=response.get("created_at"), model=response.get("model"))
                    yield frame({"role": "assistant"})
                elif kind == "response.output_text.delta":
                    yield frame({"content": event["delta"]})
                elif kind == "response.refusal.delta":
                    yield frame({"refusal": event["delta"]})
                elif kind == "response.output_item.added" and event["item"].get("type") == "function_call":
                    item = event["item"]
                    index = len(calls)
                    calls[event["output_index"]] = index
                    yield frame({"tool_calls": [{"index": index, "id": item["call_id"], "type": "function", "function": {"name": item["name"], "arguments": item.get("arguments", "")}}]})
                elif kind == "response.function_call_arguments.delta":
                    yield frame({"tool_calls": [{"index": calls[event["output_index"]], "function": {"arguments": event["delta"]}}]})
                elif kind in {"response.completed", "response.incomplete"}:
                    translated = from_responses(event["response"])
                    yield frame({}, translated["choices"][0]["finish_reason"], translated["usage"])
                    done = True
                elif kind in {"error", "response.failed"}:
                    raise ValueError("Provider stream failed")
                # Reasoning text, encrypted state, and unknown metadata are not emitted.
        if not done:
            raise ValueError("Provider stream interrupted")
        yield b"data: [DONE]\n\n"
    finally:
        await source.aclose()
