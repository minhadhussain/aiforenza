"""Live auth-page checks; never impersonates a Google user or logs credentials."""

import argparse
import json
from urllib.parse import urlsplit

import httpx
from playwright.sync_api import sync_playwright, expect
from opencode_live_test import require
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:3000")
    args = parser.parse_args()
    with httpx.Client(timeout=30) as client:
        response = client.get(settings.supabase_url.rstrip("/") + "/auth/v1/settings", headers={"apikey": settings.supabase_anon_key})
        require(response.status_code == 200, "Supabase auth settings unavailable")
        google_enabled = response.json().get("external", {}).get("google") is True
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for intent in ("login", "signup"):
                context = browser.new_context()
                page = context.new_page()
                signups = []
                page.on("request", lambda request: signups.append(True) if "/auth/v1/signup" in request.url else None)
                page.goto(args.url + "/" + intent, wait_until="networkidle", timeout=60000)
                expect(page.get_by_role("button", name="Continue with Google", exact=True)).to_have_count(1)
                alternate = "/signup" if intent == "login" else "/login"
                expect(page.locator(f'a[href="{alternate}"]')).to_have_count(1)
                require("Phase 2" not in page.locator("body").inner_text() and "wallet phase" not in page.locator("body").inner_text(), "Outdated auth copy remains")
                if intent == "signup":
                    page.get_by_label("Email", exact=True).fill("ADMIN1")
                    page.get_by_label("Password", exact=True).fill("synthetic-validation-only")
                    page.get_by_role("button", name="Create account", exact=True).click()
                    require(page.get_by_label("Email", exact=True).evaluate("input => input.validity.typeMismatch"), "Username accepted as email")
                    require(not signups, "Invalid email was sent to signup")
                page.get_by_role("button", name="Continue with Google", exact=True).click()
                if google_enabled:
                    page.wait_for_url(lambda url: url.hostname == "accounts.google.com", timeout=45000)
                else:
                    expect(page.locator("form").get_by_role("alert")).to_contain_text("Google sign-in is not enabled", timeout=45000)
                    require(urlsplit(page.url).path == "/" + intent, "OAuth error returned to wrong auth page")
                print(json.dumps({"page": intent, "google_button": True, "single_account_switch_link": True, "outdated_copy_removed": True, "google_enabled": google_enabled, "google_handoff": google_enabled, "disabled_provider_error": not google_enabled}))
                context.close()
            context = browser.new_context()
            page = context.new_page()
            page.goto(args.url + "/auth/callback?provider=google&intent=signup&error=access_denied", wait_until="networkidle")
            expect(page.locator("form").get_by_role("alert")).to_contain_text("cancelled")
            page.goto(args.url + "/auth/callback?provider=google&code=fixture-invalid-code&next=https://example.invalid", wait_until="networkidle")
            require(urlsplit(page.url).netloc == urlsplit(args.url).netloc, "Unsafe OAuth return URL")
            expect(page.locator("form").get_by_role("alert")).to_contain_text("could not be completed")
            print(json.dumps({"oauth_cancellation": True, "invalid_code_recovery": True, "external_redirect_blocked": True, "full_google_login_verified": False}))
            context.close()
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Google flow verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
