"""Inspect/sync the local chooser from enabled, priced AI Forenza models only."""

import argparse
import asyncio
import copy
import json
import os
import re
import subprocess
from pathlib import Path

import httpx
from opencode_live_test import (
    ROOT,
    state,
    save,
    require,
    snapshot,
    fingerprint,
    ORIGINAL,
    select,
)
from app.core.config import settings
from app.repositories.models import fetch_enabled_models
from app.repositories.supabase_rest import rest_select

CONFIG = Path.home() / "OneDrive/Desktop/opencode.json"


async def inspect():
    models = await fetch_enabled_models()
    rows = await rest_select(
        "/rest/v1/models",
        {
            "select": "slug,provider_model_id,enabled,pricing_verified,pricing_max_input_tokens,pricing_max_output_tokens",
            "order": "slug.asc",
        },
    )
    async with httpx.AsyncClient(timeout=45, follow_redirects=False) as client:
        response = await client.get(
            settings.azure_endpoint.rstrip("/") + "/models",
            headers={"api-key": settings.azure_api_key},
        )
        ids = []
        if response.status_code == 200:
            ids = [
                item["id"]
                for item in response.json().get("data", [])
                if isinstance(item.get("id"), str)
                and re.fullmatch(r"[A-Za-z0-9._:/-]{1,160}", item["id"])
            ]
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    print(
        json.dumps(
            {
                "azure_list_status": response.status_code,
                "azure_model_count": len(ids),
                "catalog_models_listed_by_azure": [
                    r["slug"] for r in rows if r["provider_model_id"] in ids
                ],
                "catalog": rows,
                "billable_models": [m.slug for m in models],
                "desktop_model_ids": list(
                    config.get("provider", {}).get("aiforenza", {}).get("models", {})
                ),
            },
            indent=2,
        )
    )
    return models


def merged_config(config, models):
    updated = copy.deepcopy(config)
    provider = updated["provider"]["aiforenza"]
    require(provider["npm"] == "@ai-sdk/openai-compatible", "Unexpected provider SDK")
    require(
        provider["options"]["baseURL"]
        in ("http://localhost:8000/v1", "http://127.0.0.1:8000/v1"),
        "Unexpected provider base URL",
    )
    entries = provider.setdefault("models", {})
    for model in models:
        # Conservative client limits; never exceed the backend's verified pricing band.
        output = min(32000, model.pricing_max_output_tokens)
        context = min(128000, model.pricing_max_input_tokens + output)
        entry = entries.setdefault(model.slug, {})
        entry["name"] = model.display_name
        if model.slug == "gpt-6-astra":
            entry["reasoning"] = False
            entry["options"] = {**entry.get("options", {}), "reasoningEffort": "none"}
            entry["options"].pop("reasoning_effort", None)
        existing_limits = entry.get("limit", {})
        entry["limit"] = {
            **existing_limits,
            "context": min(existing_limits.get("context", context), context),
            "output": min(existing_limits.get("output", output), output),
        }
        input_limit = max(
            1,
            min(
                90000,
                (model.pricing_max_input_tokens - 8192) // 2,
                entry["limit"]["context"] - entry["limit"]["output"],
            ),
        )
        entry["limit"]["input"] = min(
            existing_limits.get("input", input_limit), input_limit
        )
    updated["compaction"] = {
        **updated.get("compaction", {}),
        "auto": True,
        "prune": True,
        "reserved": 16000,
    }
    return updated


def sync():
    models = asyncio.run(inspect())
    require(models, "No priced/enabled models to sync")
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    private = state()
    private.setdefault("model_chooser_backup", CONFIG.read_text(encoding="utf-8"))
    save(private)
    updated = merged_config(config, models)
    CONFIG.write_text(json.dumps(updated, indent=2) + "\n", encoding="utf-8")
    # Confirm credential/default choices were preserved, without displaying them.
    require(
        updated["provider"]["aiforenza"]["options"]
        == config["provider"]["aiforenza"]["options"],
        "Provider credentials changed",
    )
    require(
        updated.get("model") == config.get("model")
        and updated.get("small_model") == config.get("small_model"),
        "Defaults changed",
    )
    print(
        json.dumps(
            {
                "synced": [m.slug for m in models],
                "credentials_and_defaults_preserved": True,
            }
        )
    )


def check():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    provider = config["provider"]["aiforenza"]
    with httpx.Client(timeout=30) as client:
        response = client.get(
            provider["options"]["baseURL"] + "/models",
            headers={"Authorization": "Bearer " + provider["options"]["apiKey"]},
        )
    require(response.status_code == 200, "API models unavailable")
    ids = [m["id"] for m in response.json()["data"]]
    require(set(ids).issubset(provider["models"]), "Chooser missing API models")
    env = {k: v for k, v in os.environ.items() if not k.startswith("OPENCODE_")}
    executable = (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )
    result = subprocess.run(
        [str(executable), "models", "aiforenza"],
        cwd=CONFIG.parent,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    require(result.returncode == 0, "OpenCode model listing failed")
    visible = re.findall(r"aiforenza/[A-Za-z0-9._-]+", result.stdout)
    require(
        all("aiforenza/" + slug in visible for slug in ids),
        "OpenCode CLI did not load every API model",
    )
    print(json.dumps({"api_models": ids, "opencode_models": visible}, indent=2))


def client_diagnose():
    logs = sorted(
        (Path.home() / ".local/share/opencode/log").glob("*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:2]
    decoder = json.JSONDecoder()
    for path in logs:
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in re.finditer(r"\{", text):
            try:
                obj, _ = decoder.raw_decode(text, match.start())
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            payload = obj.get("requestBodyValues", {})
            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except ValueError:
                    continue
            if not isinstance(payload, dict) or payload.get("model") != "gpt-6-astra":
                continue
            print(
                json.dumps(
                    {
                        "request_fields": list(payload),
                        "reasoning_effort": payload.get("reasoning_effort")
                        if payload.get("reasoning_effort")
                        in ("none", "low", "medium", "high")
                        else None,
                        "max_tokens": payload.get("max_tokens")
                        if isinstance(payload.get("max_tokens"), int)
                        else None,
                        "tool_count": len(payload.get("tools", [])),
                        "status": obj.get("statusCode")
                        if isinstance(obj.get("statusCode"), int)
                        else None,
                    }
                )
            )
    private = state()
    after = snapshot(private["user_id"])
    print(
        json.dumps(
            {
                "balance_cents": after["wallet"]["balance_cents"],
                "reserved_cents": after["wallet"]["reserved_cents"],
                "recent_usage": [
                    {k: r[k] for k in ("request_id", "status", "customer_charge_cents")}
                    for r in select("usage_records", private["user_id"])[-3:]
                ],
            }
        )
    )


def client_check():
    private = state()
    before = snapshot(private["user_id"])
    old_ids = {r["request_id"] for r in select("usage_records", private["user_id"])}
    historical = fingerprint(snapshot(ORIGINAL))
    require(not before["holds"], "Existing holds need review")
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            (
                "OPENCODE_",
                "AZURE_",
                "SUPABASE_",
                "STRIPE_",
                "DATABASE_",
                "API_KEY_",
                "LITELLM_",
            )
        )
    }
    env["OPENCODE_DISABLE_AUTOUPDATE"] = "true"
    desktop = json.loads(CONFIG.read_text(encoding="utf-8"))
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps(
        {
            "provider": {"aiforenza": desktop["provider"]["aiforenza"]},
            "enabled_providers": ["aiforenza"],
            "share": "disabled",
            "agent": {"title": {"disable": True}},
        }
    )
    env["OPENCODE_DISABLE_DEFAULT_PLUGINS"] = "true"
    env["OPENCODE_DISABLE_CLAUDE_CODE"] = "true"
    env["OPENCODE_CONFIG"] = str(CONFIG)
    executable = (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )
    child = subprocess.Popen(
        [
            str(executable),
            "run",
            "--print-logs",
            "--format",
            "json",
            "--model",
            "aiforenza/gpt-6-astra",
            "--title",
            "AI Forenza Astra chooser verification",
            "Reply OK. Do not use tools or inspect files.",
        ],
        cwd=ROOT / "tools/.opencode-test-workspace",
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        stdout, stderr = child.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        child.kill()
        stdout, stderr = child.communicate()
    events = []
    for line in stdout.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        except ValueError:
            pass
    result = {
        "diagnostic_sizes": {"stdout": len(stdout), "stderr": len(stderr)},
        "startup_services": sorted(set(re.findall(r"service=([a-zA-Z_.-]+)", stderr))),
        "error_categories": [
            p
            for p in (
                "Session not found",
                "SQLITE_BUSY",
                "database is locked",
                "Configuration is invalid",
                "Invalid config",
                "Model not found",
            )
            if p in stderr or p in stdout
        ],
        "exit_code": child.returncode,
        "event_types": [e.get("type") for e in events],
        "stderr_categories": [
            p
            for p in ("error", "retry", "install", "permission", "lock", "timeout")
            if p in stderr.lower()
        ],
        "text_received": any(e.get("type") == "text" for e in events),
        "errors": sum(e.get("type") == "error" for e in events),
        "finish_reasons": [
            e.get("part", {}).get("reason")
            for e in events
            if e.get("type") == "step_finish"
        ],
    }
    print(json.dumps(result), flush=True)
    require(
        child.returncode == 0 and result["text_received"] and not result["errors"],
        "Actual OpenCode Astra request failed",
    )
    rows = [
        r
        for r in select("usage_records", private["user_id"])
        if r["request_id"] not in old_ids
    ]
    after = snapshot(private["user_id"])
    require(
        len(rows) == 1 and rows[0]["status"] == "completed",
        "Expected one completed usage record",
    )
    charges = [
        t
        for t in after["transactions"]
        if t["reference_id"] == "usage:" + rows[0]["request_id"]
    ]
    require(
        len(charges) == 1
        and charges[0]["amount_cents"] == -rows[0]["customer_charge_cents"],
        "Incorrect usage settlement",
    )
    require(
        not after["holds"] and fingerprint(snapshot(ORIGINAL)) == historical,
        "Wallet hold invariants changed",
    )
    print(
        json.dumps(
            {
                "request_id": rows[0]["request_id"],
                "charge_cents": rows[0]["customer_charge_cents"],
                "before_cents": before["wallet"]["balance_cents"],
                "after_cents": after["wallet"]["balance_cents"],
                "reserved_cents": 0,
                "historical_unchanged": True,
            }
        )
    )


def diagnose():
    """Bounded provider checks; print only allowlisted parameter/error categories."""
    with httpx.Client(timeout=90, follow_redirects=False) as client:
        for slug in ("gpt-6-astra",):
            response = client.post(
                settings.azure_endpoint.rstrip("/") + "/chat/completions",
                headers={"api-key": settings.azure_api_key},
                json={
                    "model": slug,
                    "messages": [{"role": "user", "content": "Reply OK."}],
                    "max_completion_tokens": 32,
                    "reasoning_effort": "none",
                    "stream": True,
                    "stream_options": {"include_usage": True},
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "test_tool",
                                "description": "Unused test tool",
                                "parameters": {"type": "object", "properties": {}},
                            },
                        }
                    ],
                    "tool_choice": "auto",
                },
            )
            error = (
                response.json().get("error", {}) if response.status_code != 200 else {}
            )
            message = str(error.get("message", ""))
            print(
                json.dumps(
                    {
                        "model": slug,
                        "status": response.status_code,
                        "mentioned_parameters": [
                            p
                            for p in (
                                "max_tokens",
                                "max_completion_tokens",
                                "stream",
                                "stream_options",
                                "tools",
                                "tool_choice",
                                "parameters",
                                "additionalProperties",
                                "strict",
                            )
                            if p in message
                        ],
                        "validation_terms": [
                            p
                            for p in (
                                "unsupported",
                                "minimum",
                                "at least",
                                "required",
                                "schema",
                                "Invalid",
                            )
                            if p in message
                        ],
                        "unsupported_parameter": error.get("code")
                        == "unsupported_parameter",
                        "tool_limit_categories": [
                            p
                            for p in (
                                "not supported",
                                "does not support",
                                "not available",
                                "disabled",
                                "not enabled",
                                "function",
                                "reasoning",
                                "requires",
                                "allowed",
                                "not implemented",
                                "coming soon",
                            )
                            if p.lower() in message.lower()
                        ],
                        "error_code": error.get("code")
                        if isinstance(error.get("code"), str)
                        and re.fullmatch(r"[A-Za-z_]{1,80}", error["code"])
                        else None,
                        "mentions_max_tokens": "max_tokens" in message,
                        "mentions_max_completion_tokens": "max_completion_tokens"
                        in message,
                    }
                )
            )


def smoke():
    models = asyncio.run(fetch_enabled_models())
    provider = json.loads(CONFIG.read_text(encoding="utf-8"))["provider"]["aiforenza"]
    private = state()
    from app.services.api_keys import authenticate_api_key

    key = asyncio.run(authenticate_api_key(provider["options"]["apiKey"]))
    require(
        key and key["user_id"] == private["user_id"],
        "Smoke test must use the funded test account",
    )
    before = snapshot(key["user_id"])
    historical = fingerprint(snapshot(ORIGINAL))
    require(not before["holds"], "Existing test holds need review before smoke tests")
    results = []
    with httpx.Client(timeout=120) as client:
        for model in models:
            if model.slug == "gpt-5.4":
                continue
            response = client.post(
                provider["options"]["baseURL"] + "/chat/completions",
                headers={"Authorization": "Bearer " + provider["options"]["apiKey"]},
                json={
                    "model": model.slug,
                    **(
                        {"reasoning_effort": "none"}
                        if model.slug == "gpt-6-astra"
                        else {}
                    ),
                    "messages": [
                        {"role": "user", "content": "Reply OK. Do not use tools."}
                    ],
                    "max_tokens": 32,
                    "stream": True,
                    "tools": [
                        {
                            "type": "function",
                            "function": {
                                "name": "test_tool",
                                "description": "Unused test tool",
                                "parameters": {"type": "object", "properties": {}},
                            },
                        }
                    ],
                    "tool_choice": "auto",
                },
            )
            rid = response.headers.get("x-request-id")
            complete = response.status_code == 200 and "data: [DONE]" in response.text
            usage = [
                r
                for r in select("usage_records", key["user_id"])
                if r["request_id"] == rid
            ]
            after = snapshot(key["user_id"])
            charges = [
                t
                for t in after["transactions"]
                if t["reference_id"] == "usage:" + str(rid)
            ]
            if complete:
                require(
                    len(usage) == len(charges) == 1,
                    "Completed request not settled exactly once",
                )
                require(
                    charges[0]["amount_cents"] == -usage[0]["customer_charge_cents"],
                    "Debit mismatch",
                )
            results.append(
                {
                    "model": model.slug,
                    "status": response.status_code,
                    "stream_complete": complete,
                    "request_id": rid,
                    "charge_cents": usage[0]["customer_charge_cents"]
                    if usage
                    else None,
                }
            )
            print(json.dumps(results[-1]), flush=True)
            require(
                not after["holds"],
                "Smoke test has unresolved hold; stop rather than retry",
            )
    require(fingerprint(snapshot(ORIGINAL)) == historical, "Original account changed")
    print(
        json.dumps(
            {
                "before_cents": before["wallet"]["balance_cents"],
                "after_cents": after["wallet"]["balance_cents"],
                "reserved_cents": 0,
                "historical_unchanged": True,
            }
        )
    )
    require(
        all(r["stream_complete"] for r in results),
        "Some models need compatibility fixes",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "inspect",
            "sync",
            "check",
            "smoke",
            "diagnose",
            "client_check",
            "client_diagnose",
        ],
    )
    args = parser.parse_args()
    try:
        asyncio.run(inspect()) if args.command == "inspect" else globals()[
            args.command
        ]()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else type(exc).__name__)
        raise SystemExit(1)
