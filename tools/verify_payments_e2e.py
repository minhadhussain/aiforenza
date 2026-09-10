"""Real Stripe test checkout/webhook verification. Never emits credentials or raw payloads."""

import argparse
import asyncio
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import httpx
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
from app.core.config import settings
from app.repositories.supabase_rest import rest_select

CLI = ROOT / "tools/stripe/stripe.exe"
if not CLI.is_file():
    CLI = Path(shutil.which("stripe") or CLI)
API = "http://127.0.0.1:8000/v1"


def test_only():
    require(
        settings.stripe_secret_key.startswith("sk_test_")
        and settings.api_env != "production",
        "Test Stripe environment required",
    )


def stripe_get(path, params=None):
    test_only()
    with httpx.Client(timeout=45) as client:
        response = client.get(
            "https://api.stripe.com/v1/" + path,
            auth=(settings.stripe_secret_key, ""),
            params=params,
        )
    require(
        response.status_code == 200,
        "Stripe lookup failed: HTTP " + str(response.status_code),
    )
    return response.json()


def auth():
    private = state()
    with httpx.Client(timeout=45) as client:
        response = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": private["email"], "password": private["password"]},
        )
    require(response.status_code == 200, "Test login failed")
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def audit():
    test_only()
    rows = asyncio.run(
        rest_select(
            "/rest/v1/topups",
            {
                "select": "id,user_id,status,amount_cents,stripe_checkout_session_id,created_at",
                "order": "created_at.desc",
                "limit": "50",
            },
        )
    )
    for row in rows:
        session_id = row["stripe_checkout_session_id"]
        payment = (
            stripe_get("checkout/sessions/" + session_id)
            if session_id.startswith("cs_test_")
            else {}
        )
        transactions = asyncio.run(
            rest_select(
                "/rest/v1/transactions",
                {
                    "reference_id": "eq.stripe:" + session_id,
                    "select": "id,amount_cents,user_id",
                },
            )
        )
        print(
            json.dumps(
                {
                    "topup_id": row["id"],
                    "user_id": row["user_id"],
                    "db_status": row["status"],
                    "usd_cents": row["amount_cents"],
                    "stripe_status": payment.get("status"),
                    "payment_status": payment.get("payment_status"),
                    "ledger_credits": len(transactions),
                    "paid_but_not_credited": payment.get("payment_status") == "paid"
                    and not transactions,
                }
            )
        )


def listener():
    test_only()
    env = os.environ.copy()
    env["STRIPE_API_KEY"] = settings.stripe_secret_key
    result = subprocess.run(
        [str(CLI), "listen", "--print-secret"],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    found = re.search(r"whsec_[A-Za-z0-9]+", result.stdout + result.stderr)
    require(
        result.returncode == 0 and found is not None,
        "Could not obtain CLI signing secret",
    )
    require(
        found.group() == settings.stripe_webhook_secret,
        "CLI signing secret differs from backend; update STRIPE_WEBHOOK_SECRET privately and restart API",
    )
    print("Stripe test listener signing secret matches backend", flush=True)
    child = subprocess.Popen(
        [
            str(CLI),
            "listen",
            "--events",
            "checkout.session.completed,checkout.session.async_payment_succeeded",
            "--forward-to",
            API + "/webhooks/stripe",
        ],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        for line in child.stdout:
            safe = re.sub(r"whsec_[A-Za-z0-9]+", "[REDACTED]", line)
            safe = re.sub(r"[sr]k_(?:test|live)_[A-Za-z0-9]+", "[REDACTED]", safe)
            print(safe.rstrip(), flush=True)
    finally:
        child.terminate()


def prepare():
    test_only()
    private = state()
    require(
        not private.get("payment_e2e"),
        "Payment test already prepared; do not create duplicate checkouts",
    )
    before = snapshot(private["user_id"])
    private["payment_e2e"] = {
        "before": before,
        "original_fingerprint": fingerprint(snapshot(ORIGINAL)),
    }
    save(private)
    with httpx.Client(timeout=60) as client:
        response = client.post(
            API + "/billing/create-checkout-session",
            headers=auth(),
            json={"package_id": "starter_10"},
        )
    require(
        response.status_code == 201,
        "Checkout creation failed: HTTP " + str(response.status_code),
    )
    result = response.json()
    require(result["session_id"].startswith("cs_test_"), "Not a test checkout")
    private["payment_e2e"]["checkout"] = result
    save(private)
    print(
        json.dumps(
            {
                "session_id": result["session_id"],
                "usd_credit_cents": result["package_value_usd_cents"],
                "inr_minor_units": result["stripe_amount_inr"],
                "before_cents": before["wallet"]["balance_cents"],
            }
        )
    )


def browser():
    from playwright.sync_api import sync_playwright, Error

    test_only()
    private = state()
    checkout = private["payment_e2e"]["checkout"]
    session = stripe_get("checkout/sessions/" + checkout["session_id"])
    require(session["livemode"] is False, "Live checkout refused")
    require(session["payment_status"] != "paid", "Already paid; run verify instead")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(checkout["checkout_url"], wait_until="domcontentloaded")
        page.locator('input[name="cardNumber"]').fill("4000003560000008", timeout=60000)
        page.locator('input[name="cardExpiry"]').fill("12/34")
        page.locator('input[name="cardCvc"]').fill("123")
        name = page.locator('input[name="billingName"]')
        if name.count():
            name.fill("AI Forenza Test")
        country = page.locator('select[name="billingCountry"]')
        if country.count():
            country.select_option("IN")
        postal = page.locator('input[name="billingPostalCode"]')
        if postal.count() and postal.is_visible():
            postal.fill("560001")
        page.get_by_test_id("hosted-payment-submit-button").click()
        authenticated = False
        for _ in range(90):
            for frame in page.frames:
                button = frame.locator("#test-source-authorize-3ds")
                try:
                    if button.count() and button.is_visible():
                        button.click()
                        authenticated = True
                except Error:
                    if not frame.is_detached():
                        raise
            if page.url.startswith(settings.next_public_app_url.rstrip("/") + "/"):
                break
            page.wait_for_timeout(1000)
        result = stripe_get("checkout/sessions/" + checkout["session_id"])
        print(
            json.dumps(
                {
                    "stripe_status": result["status"],
                    "payment_status": result["payment_status"],
                    "three_ds_completed": authenticated,
                    "returned_to_app": page.url.startswith(
                        settings.next_public_app_url.rstrip("/") + "/"
                    ),
                }
            )
        )
        require(
            result["payment_status"] == "paid", "Browser test payment not completed"
        )
        browser.close()


def verify():
    private = state()
    data = private["payment_e2e"]
    checkout = data["checkout"]
    session = stripe_get("checkout/sessions/" + checkout["session_id"])
    require(
        session["payment_status"] == "paid"
        and session["status"] == "complete"
        and not session["livemode"],
        "Stripe test payment not paid",
    )
    rows = asyncio.run(
        rest_select(
            "/rest/v1/topups",
            {
                "stripe_checkout_session_id": "eq." + checkout["session_id"],
                "select": "*",
            },
        )
    )
    after = snapshot(private["user_id"])
    credits = [
        t
        for t in after["transactions"]
        if t["reference_id"] == "stripe:" + checkout["session_id"]
    ]
    require(
        rows[0]["status"] == "COMPLETED" and len(credits) == 1,
        "Paid checkout not credited exactly once",
    )
    require(
        credits[0]["amount_cents"] == 1000
        and credits[0]["balance_after_cents"]
        == data["before"]["wallet"]["balance_cents"] + 1000,
        "Topup delta incorrect",
    )
    require(
        sum(t["amount_cents"] for t in after["transactions"])
        == after["wallet"]["balance_cents"],
        "Wallet balance does not match its ledger",
    )
    require(
        fingerprint(snapshot(ORIGINAL)) == data["original_fingerprint"],
        "Original account changed",
    )
    require(after["holds"] == data["before"]["holds"], "Reservations changed")
    events = stripe_get("events", {"type": "checkout.session.completed", "limit": 100})[
        "data"
    ]
    matching = [
        e for e in events if e["data"]["object"]["id"] == checkout["session_id"]
    ]
    require(len(matching) == 1, "Cannot identify original Stripe event")
    data["event_id"] = matching[0]["id"]
    data["report"] = {
        "event_id": data["event_id"],
        "session_id": checkout["session_id"],
        "before_cents": data["before"]["wallet"]["balance_cents"],
        "after_cents": credits[0]["balance_after_cents"],
        "current_balance_cents": after["wallet"]["balance_cents"],
        "credit_cents": 1000,
        "inr_minor_units": session["amount_total"],
        "topup_status": rows[0]["status"],
        "credit_count": 1,
        "reserved_cents": after["wallet"]["reserved_cents"],
        "original_unchanged": True,
    }
    save(private)
    print(json.dumps(data["report"], indent=2))


def replay():
    test_only()
    private = state()
    event_id = private["payment_e2e"]["event_id"]
    before = fingerprint(snapshot(private["user_id"]))
    env = {**os.environ, "STRIPE_API_KEY": settings.stripe_secret_key}
    result = subprocess.run(
        [str(CLI), "events", "resend", event_id],
        env=env,
        capture_output=True,
        text=True,
        timeout=45,
    )
    require(
        result.returncode == 0, "Stripe CLI resend failed; no replay success claimed"
    )
    time.sleep(5)
    require(
        fingerprint(snapshot(private["user_id"])) == before,
        "Replay altered wallet or ledger",
    )
    print(
        json.dumps(
            {
                "event_id": event_id,
                "stripe_cli_resend": True,
                "wallet_ledger_unchanged": True,
            }
        )
    )


def browser_verify():
    from playwright.sync_api import sync_playwright, expect, TimeoutError
    from urllib.parse import urlsplit

    private = state()
    balance = snapshot(private["user_id"])["wallet"]["available_balance_cents"]
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        statuses = []
        page.on(
            "response",
            lambda response: (
                statuses.append(response.status)
                if "/auth/v1/token" in response.url
                else None
            ),
        )
        base = settings.next_public_app_url.rstrip("/")
        print("Browser stage: login page", flush=True)
        page.goto(base + "/login", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle")
        page.get_by_label("Email", exact=True).fill(private["email"])
        page.get_by_label("Password", exact=True).fill(private["password"])
        page.wait_for_timeout(500)
        require(
            page.get_by_label("Email", exact=True).input_value() == private["email"]
            and page.get_by_label("Password", exact=True).input_value()
            == private["password"],
            "Login form values reset during hydration",
        )
        page.get_by_role("button", name="Log in", exact=True).click()
        print("Browser stage: submitted login", flush=True)
        try:
            page.wait_for_url(
                "**/dashboard", timeout=60000, wait_until="domcontentloaded"
            )
        except TimeoutError:
            print(
                json.dumps(
                    {
                        "auth_http_statuses": statuses,
                        "current_path": urlsplit(page.url).path,
                        "form_valid": page.locator("form").evaluate(
                            "form => form.checkValidity()"
                        )
                        if page.locator("form").count()
                        else None,
                        "invalid_login_message": "Invalid login credentials"
                        in page.locator("body").inner_text(),
                    }
                )
            )
            raise
        print("Browser stage: authenticated dashboard", flush=True)
        session_id = private["payment_e2e"]["checkout"]["session_id"]
        page.goto(
            base + "/dashboard/billing?success=true&session_id=" + session_id,
            wait_until="domcontentloaded",
        )
        print("Browser stage: billing confirmation", flush=True)
        expect(page.get_by_role("status")).to_contain_text(
            "Payment verified. $10.00 has been added", timeout=45000
        )
        expected = f"${balance / 100:.2f}"
        expect(page.get_by_text(expected, exact=True)).to_be_visible()
        page.get_by_role("button", name="Refresh balance and top-ups").click()
        expect(page.get_by_text(expected, exact=True)).to_be_visible()
        page.goto(
            base + "/dashboard/billing?success=true&session_id=cs_test_nonexistent",
            wait_until="domcontentloaded",
        )
        expect(page.get_by_role("status")).not_to_contain_text("Payment verified")
        page.goto(
            base + "/dashboard/billing?cancelled=true", wait_until="domcontentloaded"
        )
        expect(page.get_by_role("status")).to_contain_text("Checkout cancelled")
        print(
            json.dumps(
                {
                    "browser_login": True,
                    "credited_notice": True,
                    "balance_display": expected,
                    "fake_success_not_credited": True,
                    "cancel_notice": True,
                }
            )
        )
        browser.close()


def api():
    from app.models.catalog import CatalogModel
    from app.models.usage import UsageMetrics
    from app.services.pricing import calculate_pricing_breakdown

    private = state()
    data = private["payment_e2e"]
    require(
        not data.get("api_started"),
        "Post-payment API test already attempted; inspect results instead",
    )
    before = snapshot(private["user_id"])
    data["api_started"] = True
    save(private)
    ids = []
    with httpx.Client(timeout=90) as client:
        headers = {"Authorization": "Bearer " + private["api_key"]}
        models = client.get(API + "/models", headers=headers)
        require(models.status_code == 200, "Model listing failed")
        for stream in (False, True):
            response = client.post(
                API + "/chat/completions",
                headers=headers,
                json={
                    "model": "gpt-5.4",
                    "messages": [
                        {"role": "user", "content": "Reply with one word: hello."}
                    ],
                    "max_completion_tokens": 128,
                    "stream": stream,
                },
            )
            require(response.status_code == 200, "Post-topup API request failed")
            require(
                ("data: [DONE]" in response.text)
                if stream
                else bool(response.json().get("usage")),
                "Incomplete response",
            )
            ids.append(response.headers["x-request-id"])
    rows = [
        r for r in select("usage_records", private["user_id"]) if r["request_id"] in ids
    ]
    require(len(rows) == 2 and len(set(ids)) == 2, "Usage not exactly once per request")
    after = snapshot(private["user_id"])
    require(after["holds"] == before["holds"] == [], "API request leaked reservation")
    summaries = []
    for row in rows:
        model = CatalogModel.model_validate(
            asyncio.run(
                rest_select(
                    "/rest/v1/models", {"id": "eq." + row["model_id"], "select": "*"}
                )
            )[0]
        )
        require(model.discount_percent == 40, "Unexpected discount")
        pricing = calculate_pricing_breakdown(
            model,
            UsageMetrics(
                input_tokens=row["input_tokens"],
                output_tokens=row["output_tokens"],
                cached_input_tokens=row["cached_input_tokens"],
            ),
        )
        require(
            pricing.customer_charge_cents == row["customer_charge_cents"],
            "Usage pricing mismatch",
        )
        charges = [
            t
            for t in after["transactions"]
            if t["reference_id"] == "usage:" + row["request_id"]
        ]
        require(
            len(charges) == 1
            and charges[0]["amount_cents"] == -row["customer_charge_cents"],
            "Usage ledger mismatch",
        )
        summaries.append(
            {
                k: row[k]
                for k in (
                    "request_id",
                    "input_tokens",
                    "output_tokens",
                    "cached_input_tokens",
                    "reference_charge_cents",
                    "customer_charge_cents",
                    "customer_savings_cents",
                )
            }
        )
    require(
        before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"]
        == sum(r["customer_charge_cents"] for r in rows),
        "Wallet debit mismatch",
    )
    require(
        fingerprint(snapshot(ORIGINAL)) == data["original_fingerprint"],
        "Original wallet changed",
    )
    data["api_report"] = {
        "requests": summaries,
        "before_cents": before["wallet"]["balance_cents"],
        "after_cents": after["wallet"]["balance_cents"],
        "reserved_cents": 0,
    }
    save(private)
    print(json.dumps(data["api_report"], indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=[
            "audit",
            "listener",
            "prepare",
            "browser",
            "verify",
            "replay",
            "browser_verify",
            "api",
        ],
    )
    args = parser.parse_args()
    try:
        globals()[args.command]()
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Payment test stopped: " + type(exc).__name__
        )
        raise SystemExit(1)
