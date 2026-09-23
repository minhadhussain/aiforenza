"""Clean OpenCode profile: real /connect Other, downloaded config, and billed usage.

--requests exercises each advertised Astra effort and the GPT-5 controls. Secrets
only enter the native credential prompt/store and are never printed. The isolated
profile is deleted and its new test key revoked on exit; ledger evidence remains.
"""

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

import httpx
from winpty import PtyProcess
from configure_opencode_global import executable
from verify_opencode_picker import read_for, stop_tui, main as verify_picker
from opencode_live_test import ROOT, state, require, snapshot, select
from app.core.config import settings
from app.repositories.models import fetch_enabled_models
from app.models.usage import UsageMetrics
from app.services.pricing import calculate_pricing_breakdown
from app.services.api_keys import list_api_keys, revoke_api_key

STAGE = "readiness"


def clean_env(root):
    env = {key: value for key, value in os.environ.items() if not key.startswith(("OPENCODE_", "AZURE_", "SUPABASE_", "STRIPE_", "DATABASE_", "LITELLM_", "API_KEY_", "AI_FORENZA_", "OPENAI_", "ANTHROPIC_"))}
    for name, directory in (("XDG_CONFIG_HOME", "config"), ("XDG_DATA_HOME", "data"), ("XDG_CACHE_HOME", "cache"), ("XDG_STATE_HOME", "state")):
        (root / directory).mkdir()
        env[name] = str(root / directory)
    env.update(OPENCODE_DISABLE_AUTOUPDATE="true", OPENCODE_DISABLE_PROJECT_CONFIG="true", OPENCODE_DISABLE_DEFAULT_PLUGINS="true", OPENCODE_DISABLE_CLAUDE_CODE="true", OPENCODE_DISABLE_EXTERNAL_SKILLS="true", TERM="xterm-256color")
    return env


def connect_via_tui(env, directory, secret, auth_path):
    global STAGE
    process = PtyProcess.spawn([str(executable()), "--pure"], cwd=str(directory), env=env, dimensions=(50, 160))
    try:
        startup = read_for(process, 25)
        STAGE = "OpenCode /connect dialog"
        process.write("/connect")
        read_for(process, 2)
        process.write("\r")
        text = read_for(process, 8)
        print(json.dumps({"tui_alive": process.isalive(), "startup_chars": len(startup), "connect_chars": len(text), "connect_dialog_visible": "connect a provider" in text.lower(), "startup_categories": [term for term in ("Get started", "Connect a provider", "Configuration is invalid", "Error", "Welcome") if term in startup + text]}), flush=True)
        require("connect a provider" in text.lower(), "Connect dialog not observed")
        STAGE = "OpenCode Other provider selection"
        process.write("other")
        text = read_for(process, 3)
        require("customprovider" in "".join(text.lower().split()), "Custom provider option not observed")
        process.write("\r")
        process.setwinsize(51, 161)  # Force a full repaint, not partial ANSI deltas.
        text = read_for(process, 3)
        require("provider id" in text.lower(), "Provider-ID prompt not observed")
        STAGE = "OpenCode provider ID and credential"
        process.write("aiforenza")
        time.sleep(0.3)
        process.write("\r")
        text = read_for(process, 3)
        require("API key" in text, "API-key prompt not observed")
        # Never print or persist terminal output containing the entered key.
        process.write(secret)
        time.sleep(0.3)
        process.write("\r")
        read_for(process, 8)
        require(auth_path.is_file(), "Isolated native credential store not created")
        saved = json.loads(auth_path.read_text(encoding="utf-8"))
        require(set(saved) == {"aiforenza"} and saved["aiforenza"].get("type") == "api" and saved["aiforenza"].get("key") == secret, "Native credential store does not match the entered key")
        print(json.dumps({"connect_other": True, "provider_id": "aiforenza", "native_credential_saved": True}), flush=True)
    finally:
        stop_tui(process)
        time.sleep(1)


def main():
    global STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--requests", action="store_true")
    parser.add_argument("--logs", type=Path)
    parser.add_argument("--timeout", type=int, default=960)
    parser.add_argument("--models", nargs="+", default=["gpt-6-astra", "gpt-5.4", "gpt-5.6-sol"])
    parser.add_argument("--efforts", nargs="+", help="Only test these advertised efforts for the selected models")
    parser.add_argument("--cleanup", action="store_true", help="Revoke only orphaned keys created by this verifier for its test account")
    args = parser.parse_args()
    private = state()
    user = private["user_id"]
    if args.cleanup:
        keys = [key for key in asyncio.run(list_api_keys(user)) if key["name"] == "Isolated OpenCode onboarding verification" and not key.get("revoked_at")]
        for key in keys:
            require(asyncio.run(revoke_api_key(user, key["id"])) is not None, "Test key cleanup failed")
        held = [hold for hold in select("wallet_reservations", user) if hold["api_key_id"] in {key["id"] for key in keys}]
        print(json.dumps({"orphaned_test_keys_revoked": len(keys), "related_holds_retained": len(held)}))
        return
    require(not args.requests or args.logs is not None, "--requests requires the safe backend --logs path")
    catalog = {model.slug: model for model in asyncio.run(fetch_enabled_models())}
    require(all(slug in catalog for slug in args.models), "Requested verification model is unavailable")
    if args.efforts:
        require(all(set(args.efforts).issubset(catalog[slug].capabilities.reasoning_efforts) for slug in args.models), "Requested verification effort is not advertised")
    old_holds = snapshot(user)["holds"]
    global_paths = [Path.home() / ".config/opencode/opencode.json", Path.home() / ".local/share/opencode/auth.json"]
    fingerprints = {p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in global_paths}
    key_id = None
    with httpx.Client(timeout=60) as client, tempfile.TemporaryDirectory(prefix="forenza-onboarding-", dir=Path.home() / "AppData/Local/Temp/opencode", ignore_cleanup_errors=True) as temporary:
        root = Path(temporary)
        env = clean_env(root)
        work = root / "work"
        work.mkdir()
        (work / "fixture.py").write_text((ROOT / "tools/fixtures/astra_effort_check.py").read_text(encoding="utf-8"), encoding="utf-8")
        downloaded = client.get(args.api + "/public/opencode-config")
        require(downloaded.status_code == 200, "Configuration download failed")
        config = downloaded.json()
        require("apiKey" not in json.dumps(config), "Downloaded config overrides the native credential store")
        require(set(config["provider"]["aiforenza"]["models"]) == set(catalog), "Download/catalog mismatch")
        login = client.post(settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password", headers={"apikey": settings.supabase_anon_key}, json={"email": private["email"], "password": private["password"]})
        require(login.status_code == 200, "Dashboard verification sign-in failed")
        auth = {"Authorization": "Bearer " + login.json()["access_token"]}
        try:
            STAGE = "new API key"
            created = client.post(args.api + "/api-keys", headers=auth, json={"name": "Isolated OpenCode onboarding verification"})
            require(created.status_code == 201, "Verification key creation failed")
            key = created.json()
            key_id = key["id"]
            secret = key["plaintext_key"]
            auth_path = root / "data/opencode/auth.json"
            require(not auth_path.exists(), "Credential profile was not empty")
            connect_via_tui(env, work, secret, auth_path)
            STAGE = "install downloaded configuration and restart"
            target = root / "config/opencode/opencode.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(config, indent=2), encoding="utf-8")
            # Test-only tool permissions/title settings; no provider or credential override.
            env["OPENCODE_CONFIG_CONTENT"] = json.dumps({"share": "disabled", "agent": {"title": {"disable": True}}, "permission": {"edit": "deny", "bash": "deny", "task": "deny", "read": "allow", "glob": "allow", "grep": "allow", "webfetch": "deny", "websearch": "deny"}})
            listed = subprocess.run([str(executable()), "models", "aiforenza"], cwd=work, env=env, capture_output=True, text=True, timeout=90)
            require(listed.returncode == 0 and all("aiforenza/" + slug in listed.stdout for slug in catalog), "Clean profile did not discover downloaded models")
            STAGE = "fresh-profile model and effort picker"
            for slug in (args.models if args.requests else ["gpt-6-astra"]):
                advertised = catalog[slug].capabilities.reasoning_efforts
                if advertised:
                    verify_picker(work, verify_variants=True, environment=env, model_slug=slug, efforts=advertised)
            print(json.dumps({"config_downloaded": True, "config_api_key_absent": True, "restart_model_ids": list(catalog), "isolated_profile": True}), flush=True)
            if args.requests:
                planned = [(slug, effort) for slug in args.models for effort in (args.efforts or catalog[slug].capabilities.reasoning_efforts or [None])]
                seen = {row["request_id"] for row in select("usage_records", user)}
                for slug, effort in planned:
                    STAGE = f"real OpenCode request {slug}/{effort or 'default'}"
                    before = snapshot(user)
                    command = [str(executable()), "run", "--pure", "--format", "json", "--model", "aiforenza/" + slug, "--title", "Clean provider verification"]
                    if effort:
                        command += ["--variant", effort]
                    command.append("Use the read tool to read fixture.py. Identify its termination bug and give the corrected line plus a brief invariant, under 120 words. Do not edit files or launch other agents.")
                    result = subprocess.run(command, cwd=work, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
                    events = []
                    for line in result.stdout.splitlines():
                        try:
                            event = json.loads(line)
                            if isinstance(event, dict):
                                events.append(event)
                        except ValueError:
                            pass
                    require(result.returncode == 0 and any(e.get("type") == "text" for e in events) and not any(e.get("type") == "error" for e in events), "OpenCode inference failed; inspect retained holds before retry")
                    require(any(e.get("type") == "tool_use" and e.get("part", {}).get("tool") == "read" and e.get("part", {}).get("state", {}).get("status") == "completed" for e in events), "Read-tool round trip not completed")
                    rows = [r for r in select("usage_records", user) if r["request_id"] not in seen]
                    require(rows and all(r["api_key_id"] == key_id for r in rows), "Requests did not use the /connect credential")
                    after = snapshot(user)
                    logs = []
                    for line in args.logs.read_text(encoding="utf-8", errors="replace").splitlines():
                        try:
                            event = json.loads(line)
                            if isinstance(event, dict):
                                logs.append(event)
                        except ValueError:
                            pass
                    for row in rows:
                        pricing = calculate_pricing_breakdown(catalog[slug], UsageMetrics(input_tokens=row["input_tokens"], output_tokens=row["output_tokens"], cached_input_tokens=row["cached_input_tokens"]))
                        require(row["customer_charge_cents"] == pricing.customer_charge_cents and row["reference_charge_cents"] == pricing.reference_charge_cents and row["billing_source"] == "PAID", "Actual usage billing mismatch")
                        ledger = [t for t in after["transactions"] if t["reference_id"] == "usage:" + row["request_id"]]
                        require(len(ledger) == 1 and ledger[0]["amount_cents"] == -pricing.customer_charge_cents, "Ledger mismatch")
                        replies = [r for r in logs if r.get("request_id") == row["request_id"] and r.get("event") == "provider_response"]
                        require(len(replies) == 1 and replies[0]["provider_status"] == 200, "Provider success evidence missing")
                        require(not effort or replies[0]["reasoning_effort"] == effort, "Selected effort did not reach the provider")
                        seen.add(row["request_id"])
                    charge = sum(r["customer_charge_cents"] for r in rows)
                    require(before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"] == charge, "Wallet delta mismatch")
                    require(after["holds"] == old_holds, "New hold retained or pre-existing holds changed")
                    print(json.dumps({"model": slug, "selected_effort": effort, "provider_status": 200, "native_credential_used": True, "stream_and_read_tool": True, "request_ids": [r["request_id"] for r in rows], "charge_cents": charge, "actual_usage_billing": True, "holds_preserved": True}), flush=True)
        finally:
            if key_id:
                try:
                    revoked = client.post(args.api + "/api-keys/" + key_id + "/revoke", headers=auth)
                    success = revoked.status_code == 200
                except httpx.HTTPError:
                    success = False
                if not success:
                    # Cleanup remains possible if the local API process stopped.
                    success = asyncio.run(revoke_api_key(user, key_id)) is not None
                require(success, "Verification key revocation needs review")
            changed = [p.name for p, old in fingerprints.items() if (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None) != old]
            # Other running OpenCode sessions can refresh their own OAuth tokens
            # during this test. The test credential must remain isolated regardless.
            if key_id:
                require(all(not p.exists() or secret.encode() not in p.read_bytes() for p in global_paths), "Test credential escaped the isolated profile")
            print(json.dumps({"test_key_revoked": key_id is not None, "test_credential_isolated": True, "original_profile_files_changed_during_run": changed}), flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("Stage:", STAGE)
        print(str(exc) if type(exc) is RuntimeError else "Onboarding verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
