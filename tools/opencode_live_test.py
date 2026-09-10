"""Explicit live OpenCode verification; never prints credentials or completion text.

Commands: serve, provision, run, verify. Private state is in a git-ignored file.
No historical reservation mutations or manual wallet credits are performed.
"""

import argparse
import asyncio
import contextvars
import hashlib
import json
import logging
import os
import secrets
import subprocess
import sys
import time
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "apps/api"))
import httpx
from app.core.config import settings
from app.repositories.supabase_rest import build_service_headers, rest_select
from app.repositories.wallets import fetch_wallet

STATE = ROOT / "tools/.opencode-test.env.local"
EVIDENCE = ROOT / "tools/opencode-live-evidence.log"
ORIGINAL = "6bdcda36-54ad-4553-98b0-d10f577a4990"
API = "http://localhost:8000/v1"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def state():
    return json.loads(STATE.read_text(encoding="utf-8"))


def save(data):
    STATE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def select(table, user, fields="*"):
    return asyncio.run(
        rest_select(
            "/rest/v1/" + table,
            {
                "user_id": "eq." + user,
                "select": fields,
                "order": "released_at.asc"
                if table == "wallet_reservation_releases"
                else "created_at.asc",
            },
        )
    )


def snapshot(user):
    wallet = asyncio.run(fetch_wallet(user))
    return {
        "wallet": wallet,
        "holds": select("wallet_reservations", user),
        "transactions": select("transactions", user),
        "releases": select("wallet_reservation_releases", user),
    }


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def serve():
    """Observe actual HTTPX responses; do not replace transport, payloads or billing."""
    import uvicorn
    from app.main import app

    context = contextvars.ContextVar("verification_scope", default=None)
    original_client = httpx.AsyncClient

    def emit(event):
        with EVIDENCE.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event) + "\n")

    async def observed_response(response):
        if (
            str(response.request.url)
            != settings.azure_endpoint.rstrip("/") + "/chat/completions"
        ):
            return
        scope = context.get() or {}
        diagnostic = {}
        if response.status_code >= 400:
            await response.aread()
            try:
                error = response.json().get("error", {})
                text = str(error.get("message", ""))
                diagnostic["mentioned_parameters"] = [
                    name
                    for name in (
                        "max_tokens",
                        "max_completion_tokens",
                        "reasoningSummary",
                        "reasoning_effort",
                        "verbosity",
                        "temperature",
                        "top_p",
                        "tools",
                        "tool_choice",
                        "parallel_tool_calls",
                    )
                    if name in text
                ]
                diagnostic["error_code"] = (
                    error.get("code")
                    if error.get("code")
                    in (
                        "unsupported_parameter",
                        "unsupported_value",
                        "invalid_request_error",
                    )
                    else "other"
                )
            except (ValueError, AttributeError):
                diagnostic["error_code"] = "unparsed"
        emit(
            {
                "kind": "azure_response",
                "request_id": scope.get("state", {}).get("request_id"),
                "status": response.status_code,
                "azure_endpoint_matched": True,
                **diagnostic,
            }
        )

    class ObservedClient(original_client):
        def __init__(self, *args, **kwargs):
            hooks = dict(kwargs.pop("event_hooks", {}) or {})
            hooks["response"] = [*hooks.get("response", []), observed_response]
            super().__init__(*args, event_hooks=hooks, **kwargs)

    httpx.AsyncClient = ObservedClient

    class SafeBalanceLog(logging.Handler):
        def emit(self, record):
            try:
                data = json.loads(record.getMessage())
                emit({"kind": "balance", **data})
            except (ValueError, TypeError):
                pass

    logger = logging.getLogger("aiforenza.balance")
    logger.setLevel(logging.INFO)
    logger.addHandler(SafeBalanceLog())
    logger.propagate = False

    async def observed_app(scope, receive, send):
        token = context.set(scope)
        status = None

        async def observed_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await app(scope, receive, observed_send)
        finally:
            if scope.get("path") == "/v1/chat/completions":
                emit(
                    {
                        "kind": "api_response",
                        "status": status,
                        "request_id": scope.get("state", {}).get("request_id"),
                        **scope.get("state", {}).get("audit", {}),
                    }
                )
            context.reset(token)

    uvicorn.run(
        observed_app, host="127.0.0.1", port=8000, access_log=False, log_level="warning"
    )


def provision():
    require(
        not STATE.exists(),
        "Private test state already exists; reuse it instead of granting another trial",
    )
    original = snapshot(ORIGINAL)
    require(
        len(original["holds"]) == 14
        and sum(h["amount_cents"] for h in original["holds"]) == 480,
        "Historical baseline differs; stop for review",
    )
    email = f"opencode-{uuid4().hex}@example.invalid"
    password = secrets.token_urlsafe(32)
    with httpx.Client(timeout=45) as client:
        # Confirm only this synthetic identity; normal dashboard bootstrap grants trial.
        response = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/admin/users",
            headers=build_service_headers(),
            json={"email": email, "password": password, "email_confirm": True},
        )
        require(response.status_code == 200, "Synthetic auth user creation failed")
        data = {
            "user_id": response.json()["id"],
            "email": email,
            "password": password,
            "original_fingerprint": fingerprint(original),
        }
        save(data)
        response = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": email, "password": password},
        )
        require(response.status_code == 200, "Test login failed")
        data["session"] = response.json()
        save(data)
        auth = {"Authorization": "Bearer " + data["session"]["access_token"]}
        for _ in range(2):
            response = client.get(API + "/dashboard/overview", headers=auth)
            require(response.status_code == 200, "Normal dashboard bootstrap failed")
            wallet = response.json()["wallet"]
            require(
                wallet["balance_cents"] == wallet["available_balance_cents"] == 500
                and wallet["reserved_cents"] == 0,
                "Trial wallet not exactly 500 available cents",
            )
        response = client.post(
            API + "/api-keys",
            headers=auth,
            json={"name": "Real OpenCode GPT-5.4 verification"},
        )
        require(response.status_code == 201, "Normal API key generation failed")
        data.update(
            api_key=response.json()["plaintext_key"],
            key_id=response.json()["id"],
            before=wallet,
        )
        save(data)
    print(
        json.dumps(
            {
                "user_id": data["user_id"],
                "key_id": data["key_id"],
                "balance_cents": 500,
                "available_cents": 500,
                "reserved_cents": 0,
            }
        )
    )


def run(retry=False):
    data = state()
    require(
        not data.get("run_started") or retry,
        "Run already attempted; verify before authorizing another request",
    )
    require(
        not select("usage_records", data["user_id"]),
        "Already has usage; do not spend again",
    )
    require(
        not select("wallet_reservations", data["user_id"]),
        "Unsettled test reservation; do not retry",
    )
    config = {
        "$schema": "https://opencode.ai/config.json",
        "autoupdate": False,
        "share": "disabled",
        "enabled_providers": ["aiforenza-test"],
        "provider": {
            "aiforenza-test": {
                "npm": "@ai-sdk/openai-compatible",
                "name": "AI Forenza fresh test",
                "options": {"baseURL": API, "apiKey": "{env:AI_FORENZA_TEST_API_KEY}"},
                "models": {
                    "gpt-5.4": {
                        "name": "GPT-5.4",
                        "limit": {"context": 128000, "output": 32000},
                    }
                },
            }
        },
        "model": "aiforenza-test/gpt-5.4",
        "small_model": "aiforenza-test/gpt-5.4",
        "agent": {"title": {"disable": True}},
    }
    # Empty isolated project avoids exposing repository secrets or prior chat content.
    workspace = ROOT / "tools/.opencode-test-workspace"
    workspace.mkdir(exist_ok=True)
    config_path = workspace / "opencode.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
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
    env.update(
        OPENCODE_CONFIG=str(config_path),
        OPENCODE_CONFIG_CONTENT=json.dumps(config),
        AI_FORENZA_TEST_API_KEY=data["api_key"],
        OPENCODE_DISABLE_AUTOUPDATE="true",
        OPENCODE_DISABLE_CLAUDE_CODE="true",
        OPENCODE_DISABLE_DEFAULT_PLUGINS="true",
    )
    command = (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )
    require(command.exists(), "OpenCode CLI unavailable")
    data["run_started"] = True
    save(data)
    evidence_offset = EVIDENCE.stat().st_size if EVIDENCE.exists() else 0
    process = subprocess.Popen(
        [
            command,
            "run",
            "--format",
            "json",
            "--model",
            "aiforenza-test/gpt-5.4",
            "--title",
            "AI Forenza live billing verification",
            "Reply with exactly FOR_ENZA_OK. Do not use tools or inspect files.",
        ],
        cwd=workspace,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    started = time.monotonic()
    stopped = False
    while True:
        try:
            stdout, stderr = process.communicate(timeout=2)
            break
        except subprocess.TimeoutExpired:
            with EVIDENCE.open("r", encoding="utf-8") as file:
                file.seek(evidence_offset)
                failed = any(
                    '"kind": "api_response"' in line and '"status": 502' in line
                    for line in file
                )
            if failed or time.monotonic() - started > 180:
                process.kill()
                stdout, stderr = process.communicate(timeout=10)
                stopped = True
                break
    events = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except ValueError:
            pass
    data["cli"] = {
        "exit_code": process.returncode,
        "stopped_after_failure_or_timeout": stopped,
        "event_types": [e.get("type") for e in events],
        "text_received": any(
            e.get("type") == "text" and bool(e.get("part", {}).get("text"))
            for e in events
        ),
        "finish_reasons": [
            e.get("part", {}).get("reason")
            for e in events
            if e.get("type") == "step_finish"
        ],
        "error_count": sum(e.get("type") == "error" for e in events),
        "stderr_present": bool(stderr.strip()),
    }
    save(data)
    print(json.dumps(data["cli"]))


def retry():
    run(retry=True)


def connect():
    """Launch interactive OpenCode using only the fresh account's provider key."""
    data = state()
    require(
        data.get("report", {}).get("historical_unchanged"),
        "Complete verification before interactive use",
    )
    workspace = ROOT / "tools/.opencode-test-workspace"
    config = json.loads((workspace / "opencode.json").read_text(encoding="utf-8"))
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
    env.update(
        AI_FORENZA_TEST_API_KEY=data["api_key"],
        OPENCODE_CONFIG_CONTENT=json.dumps(config),
        OPENCODE_DISABLE_AUTOUPDATE="true",
        OPENCODE_DISABLE_CLAUDE_CODE="true",
        OPENCODE_DISABLE_DEFAULT_PLUGINS="true",
    )
    executable = (
        Path.home()
        / "AppData/Roaming/npm/node_modules/opencode-ai/node_modules/opencode-windows-x64/bin/opencode.exe"
    )
    subprocess.run(
        [executable, "--model", "aiforenza-test/gpt-5.4"],
        cwd=workspace,
        env=env,
        check=False,
    )


def verify():
    data = state()
    rows = select("usage_records", data["user_id"])
    after = snapshot(data["user_id"])
    require(
        fingerprint(snapshot(ORIGINAL)) == data["original_fingerprint"],
        "Historical account changed",
    )
    print("Original wallet, all 14 holds, transactions and release audit unchanged")
    print("CLI", json.dumps(data.get("cli", {})))
    print(
        "New wallet",
        json.dumps(
            {
                k: after["wallet"][k]
                for k in ("balance_cents", "reserved_cents", "available_balance_cents")
            }
        ),
    )
    evidence = [
        json.loads(line) for line in EVIDENCE.read_text(encoding="utf-8").splitlines()
    ]
    decisions = [
        e
        for e in evidence
        if e.get("kind") == "balance" and e.get("user_id") == data["user_id"]
    ]
    require(
        data.get("cli", {}).get("text_received")
        and data["cli"]["error_count"] == 0
        and data["cli"]["exit_code"] == 0
        and data["cli"]["finish_reasons"] == ["stop"],
        "OpenCode did not receive a successful model response",
    )
    require(len(rows) == 1, "Expected exactly one persisted inference usage record")
    row = rows[0]
    successful_decisions = [
        e for e in decisions if e["request_id"] == row["request_id"]
    ]
    require(
        len(successful_decisions) == 1
        and successful_decisions[0]["comparison"] == "reserved",
        "Successful request reservation not proven",
    )
    print("Successful preflight", json.dumps(successful_decisions[0]))
    rejected_ids = {e["request_id"] for e in decisions} - {row["request_id"]}
    require(
        {r["request_id"] for r in after["releases"]} == rejected_ids,
        "Rejected test requests do not match release audit",
    )
    for released in after["releases"]:
        require(
            released["reason"] == "provider_rejected"
            and any(
                e.get("kind") == "azure_response"
                and e.get("request_id") == released["request_id"]
                and e.get("status") == 400
                for e in evidence
            ),
            "Release missing definitive rejection evidence",
        )
    require(
        row["api_key_id"] == data["key_id"] and row["status"] == "completed",
        "Usage identity/status mismatch",
    )
    model = asyncio.run(
        rest_select("/rest/v1/models", {"id": "eq." + row["model_id"], "select": "*"})
    )[0]
    require(
        model["slug"] == "gpt-5.4" and Decimal(str(model["discount_percent"])) == 40,
        "Unexpected model or discount",
    )
    reference = (
        Decimal(str(model["input_price_per_million"]))
        * (row["input_tokens"] - row["cached_input_tokens"])
        + Decimal(
            str(
                model["cached_input_price_per_million"]
                if model["cached_input_price_per_million"] is not None
                else model["input_price_per_million"]
            )
        )
        * row["cached_input_tokens"]
        + Decimal(str(model["output_price_per_million"])) * row["output_tokens"]
    ) / Decimal(1000000)
    customer = reference * Decimal("0.60")
    cents = lambda amount: int((amount * 100).to_integral_value(rounding=ROUND_CEILING))
    require(
        row["reference_charge_cents"] == cents(reference)
        and row["customer_charge_cents"] == cents(customer),
        "Pricing mismatch",
    )
    require(
        row["customer_savings_cents"] == cents(reference) - cents(customer),
        "Savings mismatch",
    )
    charges = [t for t in after["transactions"] if t["type"] == "USAGE"]
    trials = [t for t in after["transactions"] if t["type"] == "FREE_TRIAL"]
    require(
        len(trials) == 1 and trials[0]["amount_cents"] == 500,
        "Trial grant not exactly once",
    )
    require(
        len(charges) == 1
        and charges[0]["reference_id"] == "usage:" + row["request_id"]
        and charges[0]["amount_cents"] == -row["customer_charge_cents"],
        "Usage ledger mismatch",
    )
    require(
        500 - after["wallet"]["balance_cents"] == row["customer_charge_cents"],
        "Wallet debit mismatch",
    )
    require(
        not after["holds"] and after["wallet"]["reserved_cents"] == 0,
        "Leaked reservation",
    )
    require(
        len(after["transactions"]) == 2
        and sum(t["amount_cents"] for t in after["transactions"])
        == after["wallet"]["balance_cents"],
        "Wallet not equal to immutable ledger sum",
    )
    azure = [
        e
        for e in evidence
        if e.get("kind") == "azure_response"
        and e.get("request_id") == row["request_id"]
    ]
    require(
        len(azure) == 1 and azure[0]["status"] == 200,
        "Azure network success not proven",
    )
    with httpx.Client(timeout=45) as client:
        response = client.get(
            API + "/dashboard/overview",
            headers={"Authorization": "Bearer " + data["session"]["access_token"]},
        )
        require(response.status_code == 200, "Dashboard overview unavailable")
        overview = response.json()
        require(overview["wallet"] == after["wallet"], "Dashboard wallet mismatch")
        require(
            overview["metrics"]["api_request_count"] == 1, "Dashboard count mismatch"
        )
    report = {
        "user_id": data["user_id"],
        "key_id": data["key_id"],
        "request_id": row["request_id"],
        "input_tokens": row["input_tokens"],
        "cached_input_tokens": row["cached_input_tokens"],
        "output_tokens": row["output_tokens"],
        "reference_usd_unrounded": str(reference),
        "customer_usd_unrounded": str(customer),
        "reference_charge_cents": row["reference_charge_cents"],
        "customer_charge_cents": row["customer_charge_cents"],
        "savings_cents": row["customer_savings_cents"],
        "wallet_before_cents": 500,
        "wallet_after_cents": after["wallet"]["balance_cents"],
        "reserved_cents": 0,
        "rejected_requests_audited": len(rejected_ids),
        "preflight_customer_cents": successful_decisions[0]["customer_charge_cents"],
        "azure_http_status": 200,
        "dashboard_api_verified": True,
        "historical_unchanged": True,
    }
    data["report"] = report
    save(data)
    print(json.dumps(report, indent=2))
    payload = {
        "url": settings.supabase_url,
        "anon_key": settings.supabase_anon_key,
        "session": data["session"],
        "expected_cents": report["wallet_after_cents"],
        "email": data["email"],
    }
    result = subprocess.run(
        ["node", str(ROOT / "tools/verify_dashboard_render.cjs")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=90,
    )
    require(
        result.returncode == 0,
        "Rendered dashboard check failed (no credentials printed)",
    )
    render = json.loads(result.stdout)
    require(render["balance_verified"], "Rendered dashboard balance mismatch")
    report["dashboard_render"] = render
    save(data)
    print("Rendered dashboard", json.dumps(render))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["serve", "provision", "run", "retry", "verify", "connect"]
    )
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except Exception as exc:
        # Only our own fixed messages are safe to print; upstream exceptions can contain secrets.
        print(
            "Live verification stopped:",
            str(exc) if type(exc) is RuntimeError else type(exc).__name__,
        )
        sys.exit(1)
