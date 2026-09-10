"""Explicitly switch desktop OpenCode to the existing trial account; never print secrets."""

import argparse
import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from opencode_live_test import (
    ROOT,
    ORIGINAL,
    state,
    save,
    snapshot,
    fingerprint,
    select,
    require,
)
from app.services.api_keys import authenticate_api_key

CONFIG = Path.home() / "OneDrive/Desktop/opencode.json"


def inspect():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    data = state()
    key = asyncio.run(authenticate_api_key(data["api_key"]))
    require(
        key and key["user_id"] == data["user_id"],
        "Test key is unavailable or owner differs",
    )
    wallet = snapshot(data["user_id"])["wallet"]
    providers = []
    for name, provider in config.get("provider", {}).items():
        options = provider.get("options", {})
        if options.get("baseURL") not in (
            "http://localhost:8000/v1",
            "http://127.0.0.1:8000/v1",
        ):
            continue
        configured = options.get("apiKey")
        owner = (
            asyncio.run(authenticate_api_key(configured))
            if isinstance(configured, str) and configured.startswith("sk_")
            else None
        )
        providers.append(
            {
                "provider": name,
                "npm": provider.get("npm"),
                "baseURL": options["baseURL"],
                "key_id": owner["id"] if owner else None,
                "user_id": owner["user_id"] if owner else None,
                "models": list(provider.get("models", {})),
            }
        )
    print(
        json.dumps(
            {
                "config_path": str(CONFIG),
                "providers": providers,
                "test_user_id": data["user_id"],
                "test_key_id": key["id"],
                "test_wallet": {
                    k: wallet[k]
                    for k in (
                        "balance_cents",
                        "reserved_cents",
                        "available_balance_cents",
                    )
                },
            },
            indent=2,
        )
    )
    return config, providers, data, wallet


def switch():
    config, providers, data, wallet = inspect()
    require(len(providers) == 1, "Expected exactly one local AI Forenza provider")
    require(
        wallet["available_balance_cents"] >= 36 and wallet["reserved_cents"] == 0,
        "Test wallet cannot safely cover verification",
    )
    provider = providers[0]["provider"]
    require(
        "gpt-5.4" in config["provider"][provider].get("models", {}),
        "GPT-5.4 not defined",
    )
    require(
        not data.get("desktop_switch"),
        "Desktop switch already recorded; inspect/verify before repeating",
    )
    data["desktop_switch"] = {
        "original_config": CONFIG.read_text(encoding="utf-8"),
        "original_account_fingerprint": fingerprint(snapshot(ORIGINAL)),
        "before": snapshot(data["user_id"]),
        "usage_before_ids": [r["id"] for r in select("usage_records", data["user_id"])],
        "provider": provider,
    }
    save(data)
    # This is the existing private desktop config, not a repository config.
    config["provider"][provider]["options"]["apiKey"] = data["api_key"]
    config["model"] = provider + "/gpt-5.4"
    config["small_model"] = provider + "/gpt-5.4"
    CONFIG.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    require(
        json.loads(CONFIG.read_text(encoding="utf-8"))["provider"][provider]["options"][
            "apiKey"
        ]
        == data["api_key"],
        "Updated config did not persist",
    )
    print(
        "Desktop config switched; previous config saved in existing Git-ignored private test state."
    )


def run():
    data = state()
    recorded = data["desktop_switch"]
    require(
        not recorded.get("run_started"),
        "Verification already attempted; inspect instead of spending again",
    )
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    provider = recorded["provider"]
    require(
        config["provider"][provider]["options"]["apiKey"] == data["api_key"],
        "Desktop key changed",
    )
    recorded["run_started"] = True
    save(data)
    executable = (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )
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
    # Use actual desktop config and normal model allowance, not a synthetic direct request.
    child = subprocess.Popen(
        [
            str(executable),
            "run",
            "--format",
            "json",
            "--model",
            provider + "/gpt-5.4",
            "--title",
            "AI Forenza account switch verification",
            "Reply briefly to this greeting: hi. Do not use tools or inspect files.",
        ],
        cwd=CONFIG.parent,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    try:
        stdout, stderr = child.communicate(timeout=150)
    except subprocess.TimeoutExpired:
        child.kill()
        child.communicate()
        raise RuntimeError("OpenCode timed out; inspect test holds before retrying")
    events = []
    for line in stdout.splitlines():
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                events.append(item)
        except ValueError:
            pass
    recorded["cli"] = {
        "exit_code": child.returncode,
        "event_types": [e.get("type") for e in events],
        "text_received": any(
            e.get("type") == "text" and bool(e.get("part", {}).get("text"))
            for e in events
        ),
        "error_count": sum(e.get("type") == "error" for e in events),
        "finish_reasons": [
            e.get("part", {}).get("reason")
            for e in events
            if e.get("type") == "step_finish"
        ],
        "stderr_present": bool(stderr.strip()),
    }
    save(data)
    print(json.dumps(recorded["cli"]))


def verify():
    data = state()
    recorded = data["desktop_switch"]
    after = snapshot(data["user_id"])
    require(
        fingerprint(snapshot(ORIGINAL)) == recorded["original_account_fingerprint"],
        "Original account changed",
    )
    rows = [
        r
        for r in select("usage_records", data["user_id"])
        if r["id"] not in recorded["usage_before_ids"]
    ]
    before_transactions = {r["id"] for r in recorded["before"]["transactions"]}
    charges = [t for t in after["transactions"] if t["id"] not in before_transactions]
    require(
        recorded.get("cli", {}).get("exit_code") == 0
        and recorded["cli"]["text_received"]
        and recorded["cli"]["error_count"] == 0,
        "Real OpenCode success not established",
    )
    require(
        len(rows) == 1 and len(charges) == 1,
        "Expected one new usage and one new charge",
    )
    row, charge = rows[0], charges[0]
    require(
        row["api_key_id"] == data["key_id"] and row["status"] == "completed",
        "Usage owner or status mismatch",
    )
    require(
        charge["type"] == "USAGE"
        and charge["reference_id"] == "usage:" + row["request_id"]
        and charge["amount_cents"] == -row["customer_charge_cents"],
        "Charge mismatch",
    )
    require(
        recorded["before"]["wallet"]["balance_cents"] - after["wallet"]["balance_cents"]
        == row["customer_charge_cents"],
        "Balance delta mismatch",
    )
    require(
        not after["holds"] and after["wallet"]["reserved_cents"] == 0,
        "Test reservation leaked",
    )
    print(
        json.dumps(
            {
                "request_id": row["request_id"],
                "key_id": row["api_key_id"],
                "before_cents": recorded["before"]["wallet"]["balance_cents"],
                "after_cents": after["wallet"]["balance_cents"],
                "reserved_cents": 0,
                "reference_cents": row["reference_charge_cents"],
                "customer_cents": row["customer_charge_cents"],
                "savings_cents": row["customer_savings_cents"],
                "input_tokens": row["input_tokens"],
                "output_tokens": row["output_tokens"],
                "original_account_unchanged": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["inspect", "switch", "run", "verify"])
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else type(exc).__name__)
        sys.exit(1)
