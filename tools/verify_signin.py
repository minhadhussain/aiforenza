"""Exercise the real browser password-login flow without printing credentials."""

import argparse
import json
import secrets
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from playwright.sync_api import sync_playwright, expect
from opencode_live_test import state
from app.core.config import settings


def verify(args, private):
    auth_statuses = []
    errors = []
    stalled = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("pageerror", lambda _: errors.append("browser_error"))
        page.on("response", lambda r: auth_statuses.append(r.status) if "/auth/v1/token" in r.url else None)
        page.goto(args.url + "/login", wait_until="networkidle", timeout=60000)
        if args.full_flow:
            page.goto(args.url + "/login?error=confirmation_failed", wait_until="networkidle")
            expect(page.locator("form").get_by_role("alert")).to_contain_text("confirmation link")
            page.get_by_label("Email", exact=True).fill(private["email"])
            page.get_by_label("Password", exact=True).fill("invalid-" + uuid4().hex)
            page.get_by_role("button", name="Log in", exact=True).click()
            expect(page.locator("form").get_by_role("alert")).to_contain_text("Invalid login credentials", timeout=30000)
            expect(page.get_by_role("button", name="Log in", exact=True)).to_be_enabled()
            print(json.dumps({"confirmation_error_visible": True, "invalid_password_retry": True}))
        if args.check_timeout:
            # Simulate a stalled auth connection, without forwarding credentials.
            page.route("**/auth/v1/token?*", lambda route: stalled.append(route))
        page.get_by_label("Email", exact=True).fill(private["email"])
        page.get_by_label("Password", exact=True).fill(private["password"])
        page.get_by_role("button", name="Log in", exact=True).click()
        if args.check_timeout:
            try:
                expect(page.get_by_role("button", name="Log in", exact=True)).to_be_enabled(timeout=30000)
                expect(page.locator("form").get_by_role("alert")).to_be_visible()
                for route in stalled:
                    route.abort()
                stalled.clear()
                page.unroute_all(behavior="ignoreErrors")
                page.get_by_role("button", name="Log in", exact=True).click()
                page.wait_for_url("**/dashboard", timeout=60000)
                expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible(timeout=60000)
                print(json.dumps({"stalled_auth_request_recovers": True, "retry_enabled": True, "retry_login_succeeded": True}))
            except Exception:
                print(json.dumps({"stalled_auth_request_recovers": False, "signing_in_stuck": page.get_by_role("button", name="Signing in...", exact=True).count() > 0}))
                raise RuntimeError("Stalled authentication leaves sign-in stuck") from None
            finally:
                for route in stalled:
                    try:
                        route.abort()
                    except Exception:
                        pass
                browser.close()
            return
        try:
            page.wait_for_url("**/dashboard", timeout=60000)
            expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible(timeout=60000)
            page.reload(wait_until="networkidle", timeout=60000)
            expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible(timeout=60000)
            if args.full_flow:
                page.get_by_role("button", name="Log out", exact=True).click()
                page.wait_for_url(args.url + "/", timeout=60000)
                page.goto(args.url + "/dashboard/api-keys", wait_until="networkidle")
                expect(page).to_have_url(args.url + "/login?next=%2Fdashboard%2Fapi-keys")
                page.get_by_label("Email", exact=True).fill(private["email"])
                page.get_by_label("Password", exact=True).fill(private["password"])
                page.get_by_role("button", name="Log in", exact=True).click()
                page.wait_for_url("**/dashboard/api-keys", timeout=60000)
                expect(page.get_by_role("heading", name="Generate a User API Key", exact=True)).to_be_visible(timeout=60000)
                page.get_by_role("button", name="Log out", exact=True).click()
                page.wait_for_url(args.url + "/", timeout=60000)
                page.goto(args.url + "/login?next=https://example.invalid", wait_until="networkidle")
                # Password managers can populate inputs without React change events.
                page.locator('input[name="email"]').evaluate("(input, value) => input.value = value", private["email"])
                page.locator('input[name="password"]').evaluate("(input, value) => input.value = value", private["password"])
                page.get_by_role("button", name="Log in", exact=True).click()
                page.wait_for_url(args.url + "/dashboard", timeout=60000)
                expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible(timeout=60000)
                print(json.dumps({"logout": True, "protected_page_redirect": True, "login_return_path": True, "external_redirect_blocked": True, "autofill_login": True}))
            print(json.dumps({"auth_statuses": auth_statuses, "login_form": "passed", "dashboard_rendered": True, "session_survives_reload": True, "browser_errors": len(errors)}))
        except Exception:
            print(json.dumps({"auth_statuses": auth_statuses, "path": urlsplit(page.url).path, "signing_in_visible": page.get_by_role("button", name="Signing in...", exact=True).count() > 0, "invalid_credentials_visible": page.get_by_text("Invalid login credentials", exact=False).count() > 0, "browser_errors": len(errors)}))
            raise RuntimeError("Browser sign-in did not complete") from None
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:3000")
    parser.add_argument("--check-timeout", action="store_true")
    parser.add_argument("--full-flow", action="store_true")
    parser.add_argument("--fresh-account", action="store_true")
    args = parser.parse_args()
    private = state()
    user_id = None
    with httpx.Client(timeout=60) as client:
        headers = {"apikey": settings.supabase_service_role_key, "Authorization": "Bearer " + settings.supabase_service_role_key}
        admin_url = settings.supabase_url.rstrip("/") + "/auth/v1/admin/users"
        try:
            if args.fresh_account:
                private = {"email": "signin-verify-" + uuid4().hex + "@example.invalid", "password": secrets.token_urlsafe(32)}
                created = client.post(admin_url, headers=headers, json={**private, "email_confirm": True})
                if created.status_code not in (200, 201):
                    raise RuntimeError("Unable to create the verification account")
                user_id = created.json()["id"]
            verify(args, private)
            if user_id:
                base = settings.supabase_url.rstrip("/") + "/rest/v1/"
                profile = client.get(base + "profiles", headers=headers, params={"id": "eq." + user_id, "select": "id"})
                wallets = client.get(base + "wallets", headers=headers, params={"user_id": "eq." + user_id, "select": "balance_cents"})
                credits = client.get(base + "transactions", headers=headers, params={"user_id": "eq." + user_id, "type": "eq.FREE_TRIAL", "select": "amount_cents"})
                if profile.status_code != 200 or len(profile.json()) != 1 or wallets.json() != [{"balance_cents": 500}] or credits.json() != [{"amount_cents": 500}]:
                    raise RuntimeError("Account persistence or exactly-once signup credit verification failed")
                print(json.dumps({"supabase_profile_saved": True, "one_paid_wallet": True, "signup_credit_granted_once": True}))
        finally:
            if user_id:
                # Retain first-login wallet/ledger evidence, but retire the test login.
                result = client.put(admin_url + "/" + user_id, headers=headers, json={"ban_duration": "876000h"})
                if result.status_code != 200:
                    raise RuntimeError("Verification account retirement needs review")
                print(json.dumps({"fresh_account_tested_and_retired": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Sign-in verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
