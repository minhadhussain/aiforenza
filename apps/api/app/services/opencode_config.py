"""Credential-free OpenCode setup from the same catalog used for inference."""

from copy import deepcopy
from ipaddress import ip_address
from urllib.parse import urlsplit

from app.models.catalog import CatalogModel

PROVIDER_ID = "aiforenza"
OPENCODE_NPM = "@ai-sdk/openai-compatible"


def validate_api_base_url(value: str, *, production: bool = False) -> str:
    value = value.strip().rstrip("/")
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    local = host == "localhost" or host.endswith(".localhost")
    try:
        address = ip_address(host)
        local = local or address.is_loopback or address.is_unspecified
    except ValueError:
        pass
    if (
        not host
        or parsed.scheme not in {"http", "https"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith("/v1")
        or any(char.isspace() for char in value)
        or "\\" in value
        or (parsed.scheme == "http" and not local)
        or (production and (local or parsed.scheme != "https"))
    ):
        raise ValueError("Configure a valid public HTTPS NEXT_PUBLIC_API_BASE_URL ending in /v1")
    # Accessing port also validates malformed/out-of-range port values.
    parsed.port
    return value


def model_entry(model: CatalogModel, existing: dict | None = None) -> dict:
    """Keep established conservative client limits; derive efforts from the DB."""
    entry = deepcopy(existing or {})
    caps = model.capabilities
    entry["name"] = model.display_name
    output = min(32000, model.pricing_max_output_tokens)
    context = min(128000, model.pricing_max_input_tokens + output, caps.context or 128000)
    limits = entry.get("limit", {})
    entry["limit"] = {
        **limits,
        "context": min(limits.get("context", context), context),
        "output": min(limits.get("output", output), output),
    }
    input_limit = max(1, min(90000, (model.pricing_max_input_tokens - 8192) // 2,
                             entry["limit"]["context"] - entry["limit"]["output"]))
    entry["limit"]["input"] = min(limits.get("input", input_limit), input_limit)
    if caps.reasoning:
        if (
            not caps.reasoning_efforts
            or len(set(caps.reasoning_efforts)) != len(caps.reasoning_efforts)
            or caps.default_reasoning_effort not in caps.reasoning_efforts
        ):
            raise ValueError("Model reasoning capabilities are incomplete")
        entry.update(reasoning=True, temperature=caps.temperature, tool_call=caps.tool_call)
        options = entry.setdefault("options", {})
        for alias in ("reasoning_effort", "reasoning", "reasoningSummary"):
            options.pop(alias, None)
        if options.get("reasoningEffort") not in caps.reasoning_efforts:
            options["reasoningEffort"] = caps.default_reasoning_effort
        entry["variants"] = {effort: {"reasoningEffort": effort} for effort in caps.reasoning_efforts}
    return entry


def apply_timeouts(options: dict, models: list[CatalogModel]) -> None:
    recommended = max((m.capabilities.client_request_timeout_ms or 0 for m in models), default=0)
    if recommended:
        for name in ("timeout", "chunkTimeout"):
            if options.get(name) is not False:
                options[name] = max(options.get(name, 0), recommended)


def build_opencode_config(models: list[CatalogModel], base_url: str, *, production: bool = False) -> dict:
    if not models:
        raise ValueError("No enabled, priced models available")
    entries = {model.slug: model_entry(model) for model in models}
    default = "gpt-5.4" if "gpt-5.4" in entries else next(iter(entries))
    options = {"baseURL": validate_api_base_url(base_url, production=production)}
    apply_timeouts(options, models)
    # /connect → Other → aiforenza stores the key in OpenCode's auth store.
    # Never embed a secret, placeholder apiKey, dashboard session, or internal ID.
    return {
        "$schema": "https://opencode.ai/config.json",
        "provider": {PROVIDER_ID: {"npm": OPENCODE_NPM, "name": "AI Forenza", "options": options, "models": entries}},
        "model": f"{PROVIDER_ID}/{default}",
        "small_model": f"{PROVIDER_ID}/{default}",
        "compaction": {"auto": True, "prune": True, "reserved": 16000},
    }
