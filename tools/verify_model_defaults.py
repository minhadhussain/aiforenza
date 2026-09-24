"""Real model/default checks with one temporary key and a short-lived test API.

No dev-stack restart is required. All model calls use the real authentication,
reservation, provider, usage, and ledger code. The generated key is revoked in
finally; no secrets or completion text are printed.
"""

import asyncio
import argparse
from contextlib import contextmanager
import json
import logging
from pathlib import Path
import socket
import tempfile
import threading
import time

import httpx
import uvicorn
from winpty import PtyProcess

from opencode_live_test import state, require, snapshot, select
from configure_opencode_global import executable
from verify_opencode_onboarding import clean_env
from verify_opencode_picker import read_for, saved_variant, stop_tui
from app.main import app
from app.core.config import settings
from app.repositories.models import fetch_enabled_models
from app.services.api_keys import revoke_api_key
from app.services.pricing import calculate_pricing_breakdown
from app.models.usage import UsageMetrics

STAGE = "setup"


@contextmanager
def test_api():
    records = []

    class SafeRecords(logging.Handler):
        def emit(self, record):
            try:
                value = json.loads(record.getMessage())
                if isinstance(value, dict):
                    records.append(value)
            except ValueError:
                pass

    logger = logging.getLogger("aiforenza.provider")
    handlers, propagate = logger.handlers[:], logger.propagate
    original_url, original_env = settings.public_api_base_url, settings.api_env
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    base = f"http://127.0.0.1:{sock.getsockname()[1]}/v1"
    settings.public_api_base_url, settings.api_env = base, "test"
    logger.handlers, logger.propagate = [SafeRecords()], False
    server = uvicorn.Server(uvicorn.Config(app, log_config=None, access_log=False, lifespan="off", timeout_graceful_shutdown=5))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 15
        while not server.started and time.monotonic() < deadline and thread.is_alive():
            time.sleep(0.05)
        require(server.started, "Isolated test API failed to start")
        yield base, records
    finally:
        server.should_exit = True
        thread.join(timeout=15)
        sock.close()
        settings.public_api_base_url, settings.api_env = original_url, original_env
        logger.handlers, logger.propagate = handlers, propagate


def choose_model(process, query, dimensions):
    process.write("\x18")
    time.sleep(0.2)
    process.write("m")
    require("select model" in read_for(process, 3).lower(), "Model picker unavailable")
    process.write(query)
    read_for(process, 2)
    process.write("\r")
    process.setwinsize(*dimensions)
    result = read_for(process, 3)
    if "select variant" in result.lower():
        process.write("\r")  # Fresh model: choose the real Default item.
        read_for(process, 2)


def tui_defaults(config, secret, records, root):
    env = clean_env(root)
    config["provider"]["aiforenza"]["options"]["apiKey"] = "{env:AI_FORENZA_VERIFICATION_KEY}"
    env["AI_FORENZA_VERIFICATION_KEY"] = secret
    env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"enabled_providers": ["aiforenza"], "share": "disabled", "agent": {"title": {"disable": True}}})
    target = root / "config/opencode/opencode.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(config), encoding="utf-8")
    work = root / "work"
    work.mkdir()
    model_state = root / "state/opencode/model.json"
    process = PtyProcess.spawn([str(executable()), "--pure"], cwd=str(work), env=env, dimensions=(50, 160))
    try:
        read_for(process, 20)
        choose_model(process, "astra", (51, 161))
        require(saved_variant(model_state, "gpt-6-astra") == "default", "Fresh Astra selection did not choose Default")

        def send_and_check(expected):
            start = len(records)
            process.write("Reply with OK only. Do not use tools.")
            read_for(process, 1)
            process.write("\r")
            deadline = time.monotonic() + 240
            while time.monotonic() < deadline:
                read_for(process, 0.5)
                current = records[start:]
                settled = [r for r in current if r.get("event") == "usage_settled"]
                if settled:
                    require(all(r.get("model") == "gpt-6-astra" and r.get("reasoning_effort") == expected for r in settled), "TUI effort did not reach actual billing")
                    require(any(r.get("event") == "provider_response" and r.get("provider_status") == 200 and r.get("reasoning_effort") == expected for r in current), "Provider did not accept the expected effort")
                    read_for(process, 2)
                    return [r["request_id"] for r in settled]
                require(process.isalive(), "OpenCode exited during inference")
            raise RuntimeError("TUI inference timed out; preserve the hold for reconciliation")

        default_ids = send_and_check("medium")
        process.write("\x14")  # Explicitly request Low; it must remain supported.
        read_for(process, 2)
        require(saved_variant(model_state, "gpt-6-astra") == "low", "Explicit Low selection was not saved")
        low_ids = send_and_check("low")
        choose_model(process, "gpt-5.4", (50, 160))
        choose_model(process, "astra", (51, 161))
        require(saved_variant(model_state, "gpt-6-astra") == "low", "Switching models overwrote an explicit user choice")
        print(json.dumps({"astra_default": "medium", "default_request_ids": default_ids, "explicit_low_request_ids": low_ids, "explicit_choice_preserved": True}), flush=True)
    finally:
        stop_tui(process)


def main():
    global STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", help="Limit a follow-up check to specific enabled models")
    parser.add_argument("--skip-tui", action="store_true", help="Run only the API smoke checks")
    args = parser.parse_args()
    private = state()
    user_id = private["user_id"]
    catalog = {m.slug: m for m in asyncio.run(fetch_enabled_models())}
    require(catalog, "No enabled models to verify")
    require(not args.models or set(args.models).issubset(catalog), "Requested model is not enabled")
    before = snapshot(user_id)
    key_id = None
    report = []
    with test_api() as (base, records), httpx.Client(timeout=180) as client:
        login = client.post(settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password", headers={"apikey": settings.supabase_anon_key}, json={"email": private["email"], "password": private["password"]})
        require(login.status_code == 200 and login.json()["user"]["id"] == user_id, "Test-account login failed")
        auth = {"Authorization": "Bearer " + login.json()["access_token"]}
        try:
            created = client.post(base + "/api-keys", headers=auth, json={"name": "Astra default and model smoke verification"})
            require(created.status_code == 201, "Temporary key creation failed")
            key_id = created.json()["id"]
            secret = created.json()["plaintext_key"]
            headers = {"Authorization": "Bearer " + secret}
            discovered = client.get(base + "/models", headers=headers)
            require(discovered.status_code == 200 and {m["id"] for m in discovered.json()["data"]} == set(catalog), "Authenticated model discovery failed")
            for slug in args.models or catalog:
                for stream in (False, True):
                    STAGE = f"{slug} stream={stream}"
                    response = client.post(base + "/chat/completions", headers=headers, json={"model": slug, "messages": [{"role": "user", "content": "Reply with OK only."}], "max_tokens": 1024, "stream": stream})
                    completed = response.status_code == 200 and ("data: [DONE]" in response.text and '"error"' not in response.text if stream else bool((response.json().get("choices") or [{}])[0].get("message", {}).get("content")))
                    request_id = response.headers.get("x-request-id")
                    provider_events = [r for r in records if r.get("request_id") == request_id]
                    item = {"model": slug, "stream": stream, "status": response.status_code, "completed": completed, "request_id": request_id, "provider_statuses": [r["provider_status"] for r in provider_events if r.get("event") == "provider_response"], "provider_error_codes": [r["error_code"] for r in provider_events if r.get("error_code")]}
                    report.append(item)
                    print(json.dumps(item), flush=True)
            if not args.skip_tui:
                STAGE = "Astra default in a fresh OpenCode TUI"
                config = client.get(base + "/public/opencode-config").json()
                with tempfile.TemporaryDirectory(prefix="forenza-default-", dir=Path.home() / "AppData/Local/Temp/opencode", ignore_cleanup_errors=True) as directory:
                    tui_defaults(config, secret, records, Path(directory))
            STAGE = "usage and ledger reconciliation"
            rows = [r for r in select("usage_records", user_id) if r["api_key_id"] == key_id]
            after = snapshot(user_id)
            for row in rows:
                model = next(m for m in catalog.values() if m.id == row["model_id"])
                price = calculate_pricing_breakdown(model, UsageMetrics(input_tokens=row["input_tokens"], output_tokens=row["output_tokens"], cached_input_tokens=row["cached_input_tokens"]))
                require(row["reference_charge_cents"] == price.reference_charge_cents and row["customer_charge_cents"] == price.customer_charge_cents, "Actual-usage price mismatch")
                debit = [t for t in after["transactions"] if t["reference_id"] == "usage:" + row["request_id"]]
                require(len(debit) == 1 and debit[0]["amount_cents"] == -price.customer_charge_cents, "Ledger mismatch")
            require(len(rows) >= sum(r["completed"] for r in report) + (0 if args.skip_tui else 2), "Missing settled usage records")
            require(before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"] == sum(r["customer_charge_cents"] for r in rows), "Wallet delta mismatch")
            holds_preserved = after["holds"] == before["holds"]
            print(json.dumps({"all_tested_models_passed": all(r["completed"] for r in report), "settled_requests": len(rows), "actual_usage_billing": True, "charge_cents": sum(r["customer_charge_cents"] for r in rows), "holds_preserved": holds_preserved, "new_key_holds": [{"request_id": h["request_id"], "amount_cents": h["amount_cents"]} for h in after["holds"] if h["api_key_id"] == key_id]}), flush=True)
            require(holds_preserved, "New unresolved holds or existing holds changed")
            require(all(r["completed"] for r in report), "Some models failed; see the per-model results")
        finally:
            if key_id:
                revoked = client.post(base + "/api-keys/" + key_id + "/revoke", headers=auth)
                if revoked.status_code != 200:
                    require(asyncio.run(revoke_api_key(user_id, key_id)) is not None, "Temporary key cleanup needs review")
                denied = client.get(base + "/models", headers={"Authorization": "Bearer " + secret})
                require(denied.status_code == 401, "Revoked test key was still accepted")
                print(json.dumps({"temporary_key_id": key_id, "revoked": True, "revoked_key_status": denied.status_code}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Stage:", STAGE)
        print(str(exc) if type(exc) is RuntimeError else "Model verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
