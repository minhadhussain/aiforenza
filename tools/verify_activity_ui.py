"""Read-only browser activity checks; simulated API errors only, no inference or financial mutations."""

import json
from playwright.sync_api import sync_playwright, expect
from opencode_live_test import state, require

STAGE = "login"


def main():
    global STAGE
    private = state()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://127.0.0.1:3000/login", wait_until="networkidle")
        page.get_by_label("Email", exact=True).fill(private["email"])
        page.get_by_label("Password", exact=True).fill(private["password"])
        page.get_by_role("button", name="Log in", exact=True).click()
        page.wait_for_url("**/dashboard", wait_until="domcontentloaded", timeout=60000)
        page.goto("http://127.0.0.1:3000/dashboard/usage", wait_until="networkidle")
        expect(page.locator("article[data-request-id]").first).to_be_visible()
        page.get_by_label("Filter status", exact=True).select_option("unsettled")
        STAGE = "unsettled display"
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        expect(
            page.locator('[data-request-id="req_0c4667a644b044c3bc46e11e9f38e656"]')
        ).to_contain_text("Held: $1.26")
        page.get_by_label("Filter status", exact=True).select_option("released")
        STAGE = "released display"
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        expect(page.locator("article[data-request-id]").first).to_contain_text(
            "Released · not billed"
        )
        require(
            all(
                "Input: Not recorded" in text
                for text in page.locator("article[data-request-id]").all_inner_texts()
            ),
            "Release fabricated input usage",
        )
        page.get_by_label("Filter status", exact=True).select_option("billed")
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        rows_before = page.locator("article[data-request-id]").count()
        pattern = "**/v1/dashboard/activity?*"
        intercepted = []

        def unavailable(route):
            intercepted.append(route.request.method)
            if route.request.method == "OPTIONS":
                route.fulfill(
                    status=200,
                    headers={
                        "access-control-allow-origin": "http://127.0.0.1:3000",
                        "access-control-allow-methods": "GET,OPTIONS",
                        "access-control-allow-headers": "authorization",
                    },
                )
                return
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"detail":"Test unavailable"}',
                headers={"access-control-allow-origin": "http://127.0.0.1:3000"},
            )

        page.route(pattern, unavailable)
        STAGE = "simulated unavailable"
        page.get_by_role("button", name="Refresh usage").click()
        page.wait_for_timeout(4000)
        alerts = page.get_by_role("alert").all_inner_texts()
        print(
            json.dumps(
                {
                    "intercepted_methods": intercepted,
                    "alert_count": len(alerts),
                    "alert_categories": [
                        term
                        for term in (
                            "last successful results",
                            "Failed to fetch",
                            "timed out",
                            "Session expired",
                        )
                        if any(term in a for a in alerts)
                    ],
                }
            ),
            flush=True,
        )
        expect(
            page.get_by_role("alert").filter(has_text="last successful results")
        ).to_contain_text("last successful results", timeout=30000)
        require(
            page.locator("article[data-request-id]").count() == rows_before,
            "Temporary failure erased last good data",
        )
        page.unroute(pattern, unavailable)
        STAGE = "error recovery"
        page.get_by_role("button", name="Refresh usage").click()
        expect(
            page.get_by_role("alert").filter(has_text="last successful results")
        ).to_have_count(0, timeout=30000)

        def expired(route):
            if route.request.method == "OPTIONS":
                route.fulfill(
                    status=200,
                    headers={
                        "access-control-allow-origin": "http://127.0.0.1:3000",
                        "access-control-allow-methods": "GET,OPTIONS",
                        "access-control-allow-headers": "authorization",
                    },
                )
                return
            route.fulfill(
                status=401,
                content_type="application/json",
                body='{"detail":"Test expired"}',
                headers={"access-control-allow-origin": "http://127.0.0.1:3000"},
            )

        page.route(pattern, expired)
        STAGE = "simulated expired session"
        page.get_by_role("button", name="Refresh usage").click()
        expect(
            page.get_by_role("alert").filter(has_text="Session expired")
        ).to_contain_text("Session expired", timeout=30000)
        expect(page.locator("article[data-request-id]")).to_have_count(0)
        require(
            private["api_key"] not in page.locator("body").inner_text(),
            "Secret rendered",
        )
        print(
            json.dumps(
                {
                    "historical_unsettled_display": True,
                    "released_not_billed": True,
                    "refresh_error_keeps_last_results": True,
                    "recovery": True,
                    "simulated_401_clears_data": True,
                    "secret_not_rendered": True,
                }
            )
        )
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Activity UI check stopped: " + type(exc).__name__
        )
        print("Stage:", STAGE)
        raise SystemExit(1)
