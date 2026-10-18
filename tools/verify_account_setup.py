"""Verify new-account setup/retry with real Supabase sessions and account RPCs.

The signup response is supplied from a disposable, admin-created confirmed user;
this does not test Google's consent UI or delivery of a confirmation email.
"""

import argparse
import json
import secrets
from uuid import uuid4

import httpx
from playwright.sync_api import expect, sync_playwright

from opencode_live_test import require
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:3000")
    args = parser.parse_args()
    base = settings.supabase_url.rstrip("/")
    credentials = {
        "email": "setup-verify-" + uuid4().hex + "@example.invalid",
        "password": secrets.token_urlsafe(32),
    }
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": "Bearer " + settings.supabase_service_role_key,
    }
    user_id = None
    with httpx.Client(timeout=30) as client:
        try:
            created = client.post(base + "/auth/v1/admin/users", headers=headers,
                                  json={**credentials, "email_confirm": True})
            require(created.status_code in (200, 201), "Unable to create setup test identity")
            user_id = created.json()["id"]
            authenticated = client.post(base + "/auth/v1/token?grant_type=password",
                                        headers={"apikey": settings.supabase_anon_key}, json=credentials)
            require(authenticated.status_code == 200, "Unable to start setup test session")
            signup_response = authenticated.json()
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    signup_calls = []

                    def signup(route):
                        signup_calls.append(True)
                        route.fulfill(status=200, content_type="application/json", body=json.dumps(signup_response))

                    page.route("**/auth/v1/signup*", signup)
                    bootstrap = "**/v1/account/bootstrap"
                    page.route(bootstrap, lambda route: route.fulfill(status=503, content_type="application/json", body='{"detail":"fixture unavailable"}'))
                    page.goto(args.url + "/signup?next=/dashboard/api-keys", wait_until="networkidle")
                    page.get_by_label("Email", exact=True).fill(credentials["email"])
                    page.get_by_label("Password", exact=True).fill(credentials["password"])
                    page.get_by_role("button", name="Create account", exact=True).click()
                    page.wait_for_url("**/auth/complete?*", timeout=45000)
                    expect(page.get_by_role("button", name="Retry account setup", exact=True)).to_be_visible()
                    expect(page.get_by_role("alert")).to_contain_text("don’t need to create another account")
                    require(len(signup_calls) == 1, "Signup unexpectedly repeated")
                    page.unroute(bootstrap)
                    page.get_by_role("button", name="Retry account setup", exact=True).click()
                    page.wait_for_url("**/dashboard/api-keys", timeout=60000)
                    expect(page.get_by_role("heading", name="Generate a User API Key", exact=True)).to_be_visible()
                    require(len(signup_calls) == 1, "Setup retry resubmitted signup")

                    # This is also the page reached by a successful OAuth callback.
                    page.goto(args.url + "/auth/complete?next=/dashboard", wait_until="domcontentloaded")
                    page.wait_for_url(args.url + "/dashboard", timeout=60000)
                    expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible()
                    page.reload(wait_until="networkidle")
                    expect(page.get_by_role("heading", name="Your AI Forenza workspace", exact=True)).to_be_visible()

                    # A stalled setup request must reach an actionable error, then recover.
                    stalled = []
                    page.route(bootstrap, lambda route: stalled.append(route))
                    page.goto(args.url + "/auth/complete?next=/dashboard/api-keys", wait_until="domcontentloaded")
                    expect(page.get_by_role("button", name="Retry account setup", exact=True)).to_be_visible(timeout=35000)
                    for route in stalled:
                        route.abort()
                    page.unroute(bootstrap)
                    page.get_by_role("button", name="Retry account setup", exact=True).click()
                    page.wait_for_url("**/dashboard/api-keys", timeout=60000)

                    guest = browser.new_page()
                    guest.goto(args.url + "/auth/complete?next=/dashboard/api-keys", wait_until="domcontentloaded")
                    guest.wait_for_url("**/login?next=%2Fdashboard%2Fapi-keys", timeout=30000)
                    print(json.dumps({"confirmed_signup_response_fixture": True,
                                      "real_session_and_bootstrap": True, "setup_retry_preserves_session": True,
                                      "signup_submitted_once": True, "dashboard_deep_link": True,
                                      "session_survives_reload": True, "stalled_setup_recovers": True,
                                      "guest_redirect": True, "full_google_login_verified": False}))
                finally:
                    browser.close()
            for table, field, extra, expected in (
                ("profiles", "id", {}, 1),
                ("wallets", "user_id", {}, 1),
                ("transactions", "user_id", {"type": "eq.FREE_TRIAL"}, 1),
            ):
                result = client.get(base + "/rest/v1/" + table, headers=headers,
                                    params={field: "eq." + user_id, "select": "id", **extra})
                require(result.status_code == 200 and len(result.json()) == expected,
                        "New-account persistence or exactly-once credit check failed")
            print(json.dumps({"one_profile": True, "one_wallet": True, "one_signup_credit_after_retries": True}))
        finally:
            if user_id:
                retired = client.put(base + "/auth/v1/admin/users/" + user_id, headers=headers,
                                     json={"ban_duration": "876000h"})
                require(retired.status_code == 200, "Setup test identity retirement needs review")
                print(json.dumps({"setup_test_identity_retired": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Account setup verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
