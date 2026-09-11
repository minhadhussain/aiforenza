"""Install existing AI Forenza provider at user scope, without changing keys or other providers.

Uses this workstation's existing desktop config as the credential source and the
authenticated AI Forenza model API as the model allowlist. Never prints configs.
"""

import argparse
import asyncio
import copy
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

import httpx
from opencode_live_test import (
    ROOT,
    ORIGINAL,
    state,
    save,
    require,
    snapshot,
    fingerprint,
    select,
)
from sync_opencode_models import CONFIG, merged_config
from app.repositories.models import fetch_enabled_models
from app.services.api_keys import authenticate_api_key


def global_path():
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        / "opencode/opencode.json"
    )


def merge_provider(existing, provider):
    """Add only this provider; preserve unrelated choices, defaults and options."""
    result = copy.deepcopy(existing)
    require(
        "aiforenza" not in result.get("disabled_providers", []),
        "AI Forenza explicitly disabled; review user settings first",
    )
    result.setdefault("$schema", "https://opencode.ai/config.json")
    providers = result.setdefault("provider", {})
    previous = providers.get("aiforenza", {})
    # Do not silently replace a different account's user-wide key or endpoint.
    options = previous.get("options", {})
    for field in ("apiKey", "baseURL"):
        require(
            field not in options or options[field] == provider["options"][field],
            "Existing global provider identity differs; review before replacing",
        )
    providers["aiforenza"] = {
        **previous,
        **provider,
        "options": {**options, **provider["options"]},
        "models": {**previous.get("models", {}), **provider["models"]},
    }
    if "enabled_providers" in result and "aiforenza" not in result["enabled_providers"]:
        result["enabled_providers"] = [*result["enabled_providers"], "aiforenza"]
    return result


def install():
    target = global_path()
    require(target.parent.is_dir(), "OpenCode global configuration directory missing")
    require(
        not target.with_suffix(".jsonc").exists(),
        "Global JSONC config exists; merge it explicitly rather than overriding comments/settings",
    )
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    desktop = json.loads(CONFIG.read_text(encoding="utf-8"))
    models = asyncio.run(fetch_enabled_models())
    provider = merged_config(desktop, models)["provider"]["aiforenza"]
    key = asyncio.run(authenticate_api_key(provider["options"]["apiKey"]))
    require(key is not None, "Existing provider key is not valid")
    with httpx.Client(timeout=45) as client:
        response = client.get(
            provider["options"]["baseURL"] + "/models",
            headers={"Authorization": "Bearer " + provider["options"]["apiKey"]},
        )
    require(response.status_code == 200, "Authenticated model API unavailable")
    ids = [m["id"] for m in response.json()["data"]]
    require(
        set(ids) == {m.slug for m in models} and "gpt-6-astra" in ids,
        "Backend catalog mismatch",
    )
    # Retain existing model definitions; do not create a frontend-only Astra entry.
    result = merge_provider(existing, provider)
    private = state()
    private.setdefault(
        "global_opencode_backup",
        {"path": str(target), "existed": target.exists(), "config": existing},
    )
    save(private)
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    require(
        json.loads(target.read_text(encoding="utf-8")) == result,
        "Global config did not persist",
    )
    print(
        json.dumps(
            {
                "global_config": str(target),
                "model_ids": ids,
                "api_key_id": key["id"],
                "same_api_key_preserved": True,
                "unrelated_providers_preserved": True,
            }
        )
    )


def executable():
    return (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )


def check():
    # Deliberately don't set OPENCODE_CONFIG or inline provider overrides.
    for directory in (ROOT, CONFIG.parent, Path.home()):
        result = subprocess.run(
            [str(executable()), "models", "aiforenza"],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=90,
        )
        names = sorted(set(re.findall(r"aiforenza/[A-Za-z0-9._-]+", result.stdout)))
        require(
            result.returncode == 0 and "aiforenza/gpt-6-astra" in names,
            "Astra missing in resolved OpenCode config",
        )
        print(json.dumps({"directory": str(directory), "opencode_models": names}))


def run():
    """One real Astra client request via the global config, no web prerequisite."""
    private = state()
    require(
        not private.get("global_opencode_run_started"),
        "Global client test already attempted; inspect results before spending again",
    )
    config = json.loads(global_path().read_text(encoding="utf-8"))
    key = asyncio.run(
        authenticate_api_key(config["provider"]["aiforenza"]["options"]["apiKey"])
    )
    require(
        key and key["user_id"] == private["user_id"],
        "Live test must use existing test identity",
    )
    before = snapshot(key["user_id"])
    require(
        before["wallet"]["available_balance_cents"] > 200, "Insufficient test headroom"
    )
    old_ids = {r["request_id"] for r in select("usage_records", key["user_id"])}
    original = fingerprint(snapshot(ORIGINAL))
    private["global_opencode_run_started"] = True
    save(private)
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(
            ("AZURE_", "SUPABASE_", "DATABASE_", "STRIPE_", "LITELLM_", "API_KEY_")
        )
    }
    require(
        not any(
            env.get(k)
            for k in (
                "OPENCODE_CONFIG",
                "OPENCODE_CONFIG_CONTENT",
                "OPENCODE_CONFIG_DIR",
            )
        ),
        "Custom OpenCode overrides present; verify before client test",
    )
    env.update(
        OPENCODE_DISABLE_AUTOUPDATE="true",
        OPENCODE_DISABLE_DEFAULT_PLUGINS="true",
        OPENCODE_DISABLE_CLAUDE_CODE="true",
    )
    with tempfile.TemporaryDirectory(prefix="aiforenza-global-check-") as directory:
        child = subprocess.Popen(
            [
                str(executable()),
                "run",
                "--print-logs",
                "--format",
                "json",
                "--model",
                "aiforenza/gpt-6-astra",
                "--title",
                "Global provider verification",
                "Reply with OK only. Do not use tools or inspect files.",
            ],
            cwd=directory,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        try:
            stdout, _stderr = child.communicate(timeout=150)
        except subprocess.TimeoutExpired:
            child.kill()
            child.communicate()
            raise RuntimeError("OpenCode timeout; inspect usage/holds before retry")
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    require(
        child.returncode == 0
        and any(e.get("type") == "text" for e in events)
        and not any(e.get("type") == "error" for e in events),
        "OpenCode did not complete successfully",
    )
    after = snapshot(key["user_id"])
    records = [
        r
        for r in select("usage_records", key["user_id"])
        if r["request_id"] not in old_ids
    ]
    require(
        len(records) == 1 and records[0]["status"] == "completed",
        "Expected one completed request",
    )
    row = records[0]
    charges = [
        t
        for t in after["transactions"]
        if t["reference_id"] == "usage:" + row["request_id"]
    ]
    require(
        row["api_key_id"] == key["id"]
        and len(charges) == 1
        and charges[0]["amount_cents"] == -row["customer_charge_cents"],
        "Key/ledger mismatch",
    )
    require(
        before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"]
        == row["customer_charge_cents"],
        "Wallet delta mismatch",
    )
    require(
        after["holds"] == before["holds"]
        and fingerprint(snapshot(ORIGINAL)) == original,
        "Existing holds changed",
    )
    report = {
        "request_id": row["request_id"],
        "api_key_id": key["id"],
        "event_types": [e.get("type") for e in events],
        "customer_cents": row["customer_charge_cents"],
        "before_cents": before["wallet"]["balance_cents"],
        "after_cents": after["wallet"]["balance_cents"],
        "reserved_cents": after["wallet"]["reserved_cents"],
        "global_config_only": True,
        "no_dashboard_selection": True,
        "existing_holds_preserved": True,
    }
    private["global_opencode_result"] = report
    save(private)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["install", "check", "run"])
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Global provider operation failed: " + type(exc).__name__
        )
        raise SystemExit(1)
