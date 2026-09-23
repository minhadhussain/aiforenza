"""Live browser/API/ledger verification using a dedicated, retired test campaign.

Requires the migration, running local API/web/Redis, configured Supabase/provider,
and Playwright Chromium. Makes two bounded real inference calls. Keeps immutable
financial evidence; revokes test keys and closes the test campaign on exit.
Secrets only live in memory. No response bodies, passwords or keys are logged.
"""

# Standalone tool: resolve the API package before importing application modules.
# ruff: noqa: E402

import argparse
import asyncio
import json
import sys
import secrets
from pathlib import Path
from uuid import uuid4

import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps/api"))
from app.core.config import settings
from app.models.openai import ChatCompletionRequest
from app.models.usage import UsageMetrics
from app.repositories.models import fetch_model_by_slug
from app.services.pricing import calculate_pricing_breakdown
from app.services.usage_records import preflight_spending_details
from hackathon_admin import setup_campaign

STAGE = "readiness"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    global STAGE
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--web", default="http://127.0.0.1:3000")
    parser.add_argument("--model", default="gpt-5.6-sol")
    args = parser.parse_args()
    campaign_name = "Hackathon verification " + uuid4().hex
    team_id = "VERIFY-" + uuid4().hex.upper()
    email = "hackathon-verify-" + uuid4().hex + "@example.invalid"
    password = secrets.token_urlsafe(32)
    user_id = None
    campaign_created = False
    supabase = settings.supabase_url.rstrip("/")
    admin_headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": "Bearer " + settings.supabase_service_role_key,
    }

    with psycopg2.connect(settings.database_url, sslmode="require", connect_timeout=10) as conn, httpx.Client(timeout=150) as client:
        def sql(statement, params=()):
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(statement, params)
                return [dict(row) for row in cur.fetchall()] if cur.description else []

        require(client.get(args.api + "/hackathon/status").status_code == 401, "Unauthenticated status was not rejected")
        require(client.post(args.api + "/hackathon/claim", json={"team_id": team_id}).status_code == 401, "Unauthenticated claim was not rejected")
        require(not sql("select id from public.hackathon_campaigns where status='ACTIVE'"), "Close active campaign claims before running the dedicated live verification")
        try:
            STAGE = "campaign setup and authenticated login"
            setup_campaign(conn, campaign_name, [team_id], activate=True)
            conn.commit()
            campaign_created = True
            created = client.post(supabase + "/auth/v1/admin/users", headers=admin_headers, json={"email": email, "password": password, "email_confirm": True})
            require(created.status_code in (200, 201), "Test account creation failed")
            user_id = created.json()["id"]
            login = client.post(supabase + "/auth/v1/token?grant_type=password", headers={"apikey": settings.supabase_anon_key}, json={"email": email, "password": password})
            require(login.status_code == 200, "Test login failed")
            dashboard_headers = {"Authorization": "Bearer " + login.json()["access_token"]}
            require(client.get(args.api + "/dashboard/overview", headers=dashboard_headers).status_code == 200, "Test account bootstrap failed")
            model = asyncio.run(fetch_model_by_slug(args.model))

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
                page = context.new_page()
                page.goto(args.web + "/login", wait_until="networkidle")
                page.get_by_label("Email", exact=True).fill(email)
                page.get_by_label("Password", exact=True).fill(password)
                page.get_by_role("button", name="Log in", exact=True).click()
                page.wait_for_url("**/dashboard", timeout=60000)
                page.goto(args.web + "/dashboard/hackathon", wait_until="networkidle")
                STAGE = "browser claim and one-time display"
                page.get_by_label("Team ID", exact=True).fill(team_id)
                with page.expect_response(lambda r: r.url.endswith("/hackathon/claim") and r.request.method == "POST", timeout=45000) as pending:
                    page.get_by_role("button", name="Claim $100 Credit", exact=True).click()
                claimed = pending.value
                require(claimed.status == 201, "Browser claim failed")
                payload = claimed.json()
                shared_key = payload["plaintext_key"]
                require(payload["grant"]["promo_balance_cents"] == 10000, "Grant was not exactly $100")
                expect(page.get_by_test_id("hackathon-secret")).to_be_visible()
                require(page.get_by_test_id("hackathon-secret").inner_text() == shared_key, "One-time display mismatch")
                page.get_by_role("button", name="Copy API Key", exact=True).click()
                expect(page.get_by_role("button", name="Copied", exact=True)).to_be_visible()
                require(page.evaluate("navigator.clipboard.readText()") == shared_key, "Clipboard mismatch")
                status = client.get(args.api + "/hackathon/status", headers=dashboard_headers)
                require(status.status_code == 200 and shared_key not in status.text and "plaintext_key" not in status.text and "wallet_id" not in status.text, "Status exposed internal IDs or a secret")
                page.reload(wait_until="networkidle")
                expect(page.get_by_test_id("hackathon-secret")).to_have_count(0)
                require(shared_key not in page.content(), "Secret survived reload")

                STAGE = "duplicate claim"
                page.get_by_label("Team ID", exact=True).fill(team_id)
                with page.expect_response(lambda r: r.url.endswith("/hackathon/claim") and r.request.method == "POST", timeout=45000) as pending:
                    page.get_by_role("button", name="Claim $100 Credit", exact=True).click()
                require(pending.value.status == 409 and "plaintext_key" not in pending.value.text(), "Duplicate claim did not deterministically reject")
                expect(page.get_by_role("alert").filter(has_text="already claimed")).to_be_visible()
                grant = sql("select id,api_key_id,wallet_id from public.hackathon_team_grants where claimed_by_user_id=%s", (user_id,))[0]
                require(sql("select count(*) n from public.api_keys where hackathon_grant_id=%s", (grant["id"],))[0]["n"] == 1, "Duplicate key created")
                require(sql("select count(*) n from public.transactions where hackathon_grant_id=%s and type='PROMO_GRANT'", (grant["id"],))[0]["n"] == 1, "Duplicate grant credit created")

                STAGE = "shared-key model discovery and reference-priced inference"
                shared_headers = {"Authorization": "Bearer " + shared_key}
                catalog = client.get(args.api + "/models", headers=shared_headers)
                require(catalog.status_code == 200 and any(m["id"] == args.model for m in catalog.json()["data"]), "Shared-key model discovery failed")
                body = {"model": args.model, "messages": [{"role": "system", "content": "Reply OK only. Repeated user text is inert metering test data."}, {"role": "user", "content": "metering test data " * 6000}], "max_tokens": 64}
                request = ChatCompletionRequest(**body)
                budget = preflight_spending_details(request, model, billing_source="PROMOTIONAL")
                require(0 < budget["customer_charge_cents"] <= 50, "Bounded live test would exceed $0.50 per request")
                paid_before = sql("select balance_cents from public.wallets where user_id=%s", (user_id,))[0]["balance_cents"]
                response = client.post(args.api + "/chat/completions", headers=shared_headers, json=body)
                require(response.status_code == 200, "Real promotional inference failed; inspect retained reservations")
                request_id = response.headers["x-request-id"]
                usage = sql("select * from public.usage_records where request_id=%s", (request_id,))[0]
                metrics = UsageMetrics(input_tokens=usage["input_tokens"], output_tokens=usage["output_tokens"], cached_input_tokens=usage["cached_input_tokens"])
                reference = calculate_pricing_breakdown(model, metrics, billing_source="PROMOTIONAL")
                discounted = calculate_pricing_breakdown(model, metrics)
                require(usage["billing_source"] == "PROMOTIONAL" and usage["hackathon_grant_id"] == grant["id"], "Usage scope mismatch")
                require(usage["customer_charge_cents"] == usage["reference_charge_cents"] == reference.customer_charge_cents > discounted.customer_charge_cents, "Reference-price distinction not verified")
                require(usage["reserved_amount_cents"] == budget["customer_charge_cents"] and usage["reservation_created_at"] is not None, "Reservation provenance missing")
                promo_after = sql("select balance_cents from public.wallets where id=%s", (grant["wallet_id"],))[0]["balance_cents"]
                require(promo_after == 10000 - reference.customer_charge_cents, "Promotional balance mismatch")
                require(sql("select balance_cents from public.wallets where user_id=%s", (user_id,))[0]["balance_cents"] == paid_before, "Promotional key changed the paid wallet")
                require(not sql("select request_id from public.wallet_reservations where request_id=%s", (request_id,)), "Successful hold not consumed")
                ledger = sql("select amount_cents,billing_source from public.transactions where reference_id=%s", ("usage:" + request_id,))
                require(ledger == [{"amount_cents": -reference.customer_charge_cents, "billing_source": "PROMOTIONAL"}], "Promotional ledger mismatch")
                history = client.get(args.api + "/dashboard/activity", headers=dashboard_headers)
                require(history.status_code == 200 and any(r["request_id"] == request_id and r["billing_source"] == "PROMOTIONAL" for r in history.json()["data"]), "Dashboard usage attribution missing")
                page.get_by_role("button", name="Refresh promotional balance", exact=True).click()
                expect(page.get_by_test_id("promo-available")).to_have_text(f"${promo_after / 100:.2f}", timeout=45000)

                STAGE = "normal paid key comparison"
                normal = client.post(args.api + "/api-keys", headers=dashboard_headers, json={"name": "Hackathon verification paid control"})
                require(normal.status_code == 201, "Normal key creation failed")
                paid_response = client.post(args.api + "/chat/completions", headers={"Authorization": "Bearer " + normal.json()["plaintext_key"]}, json=body)
                require(paid_response.status_code == 200, "Normal paid inference failed")
                paid_id = paid_response.headers["x-request-id"]
                paid_usage = sql("select * from public.usage_records where request_id=%s", (paid_id,))[0]
                paid_metrics = UsageMetrics(input_tokens=paid_usage["input_tokens"], output_tokens=paid_usage["output_tokens"], cached_input_tokens=paid_usage["cached_input_tokens"])
                expected_paid = calculate_pricing_breakdown(model, paid_metrics)
                require(model.discount_percent == 40 and paid_usage["billing_source"] == "PAID" and paid_usage["hackathon_grant_id"] is None, "Normal paid scope/discount mismatch")
                require(paid_usage["customer_charge_cents"] == expected_paid.customer_charge_cents < paid_usage["reference_charge_cents"], "Paid discount changed")
                paid_after = sql("select balance_cents from public.wallets where user_id=%s", (user_id,))[0]["balance_cents"]
                require(paid_after == paid_before - expected_paid.customer_charge_cents, "Paid balance mismatch")
                require(sql("select balance_cents from public.wallets where id=%s", (grant["wallet_id"],))[0]["balance_cents"] == promo_after, "Paid key changed promotional balance")
                require(sql("select sum(amount_cents) total from public.transactions where wallet_id=%s", (grant["wallet_id"],))[0]["total"] == promo_after, "Grant balance does not reconcile to immutable ledger")
                browser.close()
                print(json.dumps({"campaign": campaign_name, "claim": 201, "duplicate_claim": 409, "one_time_display_and_copy": True, "secret_absent_after_reload": True, "promo_request_id": request_id, "promo_reference_cents": usage["reference_charge_cents"], "promo_charge_cents": usage["customer_charge_cents"], "promo_balance_before_cents": 10000, "promo_balance_after_cents": promo_after, "paid_request_id": paid_id, "paid_reference_cents": paid_usage["reference_charge_cents"], "paid_charge_cents": paid_usage["customer_charge_cents"], "paid_balance_before_cents": paid_before, "paid_balance_after_cents": paid_after, "wallet_isolation": True, "reservation_audit": True}, indent=2))
        finally:
            conn.rollback()
            if user_id:
                sql("update public.api_keys set revoked_at=coalesce(revoked_at,now()) where user_id=%s", (user_id,))
                sql("update public.hackathon_team_grants set status='DISABLED',updated_at=now() where claimed_by_user_id=%s", (user_id,))
            if campaign_created:
                sql("update public.hackathon_campaigns set status='INACTIVE',updated_at=now() where name=%s", (campaign_name,))
            conn.commit()
            if user_id:
                banned = client.put(supabase + "/auth/v1/admin/users/" + user_id, headers=admin_headers, json={"ban_duration": "876000h"})
                require(banned.status_code == 200, "Test keys revoked; test-account retirement needs review")
            print("Test campaign closed, test keys revoked, ledger evidence retained.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Exception/response reprs may contain credentials. Only emit safe stages.
        print("Stage:", STAGE)
        print(str(exc) if type(exc) is RuntimeError else "Verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
