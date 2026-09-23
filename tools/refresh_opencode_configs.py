"""Refresh existing AI Forenza model definitions; never copy/change credentials."""

import argparse
import copy
import json
from pathlib import Path

import httpx


def merge_config(current, downloaded):
    result = copy.deepcopy(current)
    source = downloaded["provider"]["aiforenza"]
    target = result.get("provider", {}).get("aiforenza")
    if target is None or target.get("npm") != "@ai-sdk/openai-compatible":
        raise ValueError("Existing AI Forenza OpenAI-compatible provider is required")
    if "apiKey" in source["options"]:
        raise ValueError("Downloaded configuration must not include credentials")
    result.setdefault("$schema", "https://opencode.ai/config.json")
    entries = target.setdefault("models", {})
    for slug, template in source["models"].items():
        old = entries.get(slug, {})
        entry = {**old, **copy.deepcopy(template)}
        entry["limit"] = {key: min(old.get("limit", {}).get(key, value), value) for key, value in template["limit"].items()}
        if template.get("reasoning"):
            options = {**old.get("options", {}), **template.get("options", {})}
            previous = old.get("options", {}).get("reasoningEffort")
            if previous in template["variants"]:
                options["reasoningEffort"] = previous
            for alias in ("reasoning_effort", "reasoning", "reasoningSummary"):
                options.pop(alias, None)
            entry["options"] = options
        entries[slug] = entry
    options = target.setdefault("options", {})
    for name in ("timeout", "chunkTimeout"):
        if name in source["options"] and options.get(name) is not False:
            options[name] = max(options.get(name, 0), source["options"][name])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--config", action="append", type=Path)
    args = parser.parse_args()
    response = httpx.get(args.api.rstrip("/") + "/public/opencode-config", timeout=30)
    response.raise_for_status()
    downloaded = response.json()
    paths = args.config or [Path.home() / ".config/opencode/opencode.json", Path.home() / "OneDrive/Desktop/opencode.json"]
    for path in paths:
        if not path.is_file():
            continue
        original = json.loads(path.read_text(encoding="utf-8"))
        updated = merge_config(original, downloaded)
        before = original["provider"]["aiforenza"].get("options", {})
        after = updated["provider"]["aiforenza"].get("options", {})
        if any(before.get(key) != after.get(key) for key in ("apiKey", "baseURL", "headers")):
            raise ValueError("Provider identity changed")
        temporary = path.with_name(path.name + ".refresh.tmp")
        try:
            temporary.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        print(json.dumps({"config": str(path), "credentials_and_defaults_preserved": True, "efforts": {slug: list(model.get("variants", {})) for slug, model in updated["provider"]["aiforenza"]["models"].items()}}))
    print("Quit and restart OpenCode to load the refreshed model definitions.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is ValueError else "Configuration refresh failed: " + type(exc).__name__)
        raise SystemExit(1)
