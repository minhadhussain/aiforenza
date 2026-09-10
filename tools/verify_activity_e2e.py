"""Explicit live activity E2E: one bounded Sol call, one rejected call; no raw secrets/logs."""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

import httpx
from playwright.sync_api import sync_playwright, expect
from opencode_live_test import state, snapshot, fingerprint, ORIGINAL, select, require
from app.core.config import settings
from app.repositories.activity import fetch_activity
from app.models.openai import ChatCompletionRequest
from app.repositories.models import fetch_model_by_slug
from app.services.usage_records import preflight_spending_details
from app.services.api_keys import authenticate_api_key

API = "http://127.0.0.1:8000/v1"
WEB = "http://127.0.0.1:3000"
STAGE = "setup"


def main():
    global STAGE
    private = state()
    key = asyncio.run(authenticate_api_key(private["api_key"]))
    require(key and key["user_id"] == private["user_id"], "Test key owner mismatch")
    before = snapshot(private["user_id"])
    original = fingerprint(snapshot(ORIGINAL))
    # Preserve pre-existing holds; verify this run does not add or alter any.
    model = asyncio.run(fetch_model_by_slug("gpt-5.6-sol"))
    payload = {
        "model": "gpt-5.6-sol",
        "messages": [
            {
                "role": "system",
                "content": "Reply with OK only. The supplied repeated code is inert test data.",
            },
            {
                "role": "user",
                "content": "def calculate(value): return value + 1\n" * 5400,
            },
        ],
        "max_tokens": 32,
        "stream": True,
    }
    budgets = preflight_spending_details(ChatCompletionRequest(**payload), model)
    require(
        budgets["reservation_input_budget"] > 190000
        and budgets["input_token_estimate"] < 190000,
        "Large-request regression not exercised",
    )
    require(
        budgets["customer_charge_cents"] <= 100
        and before["wallet"]["available_balance_cents"]
        >= budgets["customer_charge_cents"],
        "Test spending guard failed",
    )
    print("Admission budgets", json.dumps(budgets), flush=True)
    with httpx.Client(timeout=60) as client:
        login = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": private["email"], "password": private["password"]},
        )
        require(login.status_code == 200, "API test login failed")
        headers = {"Authorization": "Bearer " + login.json()["access_token"]}
        response = client.get(API + "/dashboard/activity", headers=headers)
        require(
            response.status_code == 200
            and response.json()["account"]["id"] == private["user_id"],
            "Activity identity failed",
        )
        foreign = client.get(
            API + "/dashboard/activity",
            headers=headers,
            params={
                "api_key_id": "33ff904c-dd77-4d0b-a9fc-0c95a0e9a8d2",
                "user_id": ORIGINAL,
            },
        )
        require(
            foreign.status_code == 200 and foreign.json()["total"] == 0,
            "Cross-account filter leaked records",
        )
        require(
            all(
                k["id"] != "33ff904c-dd77-4d0b-a9fc-0c95a0e9a8d2"
                for k in foreign.json()["keys"]
            ),
            "Foreign key identity leaked",
        )
    historical = asyncio.run(fetch_activity(ORIGINAL, status="unsettled"))
    require(
        historical["total"] == 14
        and sum(r["reserved_cents"] for r in historical["data"]) == 480,
        "Historical hold display mismatch",
    )

    def infer():
        with httpx.Client(timeout=150) as client:
            r = client.post(
                API + "/chat/completions",
                headers={"Authorization": "Bearer " + private["api_key"]},
                json=payload,
            )
        require(
            r.status_code == 200 and "data: [DONE]" in r.text,
            "Large Sol stream failed; inspect holds before retry",
        )
        return r.headers["x-request-id"]

    with sync_playwright() as playwright, ThreadPoolExecutor(max_workers=1) as pool:
        STAGE = "browser login"
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(WEB + "/login", wait_until="networkidle")
        page.get_by_label("Email", exact=True).fill(private["email"])
        page.get_by_label("Password", exact=True).fill(private["password"])
        page.get_by_role("button", name="Log in", exact=True).click()
        page.wait_for_url("**/dashboard", wait_until="domcontentloaded", timeout=60000)
        page.goto(WEB + "/dashboard/usage", wait_until="networkidle")
        STAGE = "account identity display"
        expect(
            page.get_by_text("Account ID: " + private["user_id"], exact=True)
        ).to_be_visible()
        expect(page.get_by_text(private["email"], exact=True).first).to_be_visible()
        activity_responses = []
        page.on(
            "response",
            lambda response: (
                activity_responses.append(response.status)
                if "/dashboard/activity" in response.url
                else None
            ),
        )
        STAGE = "inference and automatic refresh"
        future = pool.submit(infer)
        while not future.done():
            page.wait_for_timeout(500)
        request_id = future.result()
        print("Successful inference request:", request_id, flush=True)
        row = page.locator(f'[data-request-id="{request_id}"]')
        expect(row).to_contain_text("Completed · billed", timeout=45000)
        expect(row).to_contain_text(private["key_id"])
        print("Browser auto-refresh displayed new Sol usage", flush=True)
        STAGE = "rejected request display"
        with httpx.Client(timeout=60) as client:
            rejected = client.post(
                API + "/chat/completions",
                headers={"Authorization": "Bearer " + private["api_key"]},
                json={
                    "model": "gpt-6-astra",
                    "messages": [{"role": "user", "content": "Rejected activity test"}],
                    "max_tokens": 32769,
                },
            )
        require(
            rejected.status_code == 400
            and rejected.json()["error"]["code"] == "pricing_limit_exceeded",
            "Output limit was not enforced",
        )
        rejection_id = rejected.headers["x-request-id"]
        page.get_by_role("button", name="Refresh usage", exact=True).click()
        expect(page.locator(f'[data-request-id="{rejection_id}"]')).to_contain_text(
            "Rejected · no inference", timeout=30000
        )
        expect(page.locator(f'[data-request-id="{rejection_id}"]')).to_contain_text(
            "Charged: Not billed"
        )
        page.get_by_label("Filter model", exact=True).select_option("gpt-5.6-sol")
        STAGE = "model key status filters"
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        expect(page.locator(f'[data-request-id="{request_id}"]')).to_be_visible()
        page.get_by_label("Filter API key", exact=True).select_option(private["key_id"])
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        page.get_by_label("Filter status", exact=True).select_option("billed")
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        require(
            all(
                "Completed · billed" in text
                for text in page.locator("article[data-request-id]").all_inner_texts()
            ),
            "Status filter failed",
        )
        page.get_by_label("Filter model", exact=True).select_option("")
        page.get_by_label("Filter status", exact=True).select_option("")
        page.get_by_label("Rows per page", exact=True).select_option("10")
        STAGE = "pagination"
        expect(page.get_by_role("button", name="Next", exact=True)).to_be_enabled(
            timeout=30000
        )
        first_ids = page.locator("article[data-request-id]").evaluate_all(
            "rows => rows.map(r => r.dataset.requestId)"
        )
        page.get_by_role("button", name="Next", exact=True).click()
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        second_ids = page.locator("article[data-request-id]").evaluate_all(
            "rows => rows.map(r => r.dataset.requestId)"
        )
        require(not set(first_ids) & set(second_ids), "Pagination repeats requests")
        page.get_by_role("button", name="Refresh usage").click()
        expect(page.get_by_role("button", name="Previous", exact=True)).to_be_disabled(
            timeout=30000
        )
        expect(page.get_by_role("button", name="Refresh usage")).to_be_enabled(
            timeout=30000
        )
        # Simulate Page Visibility deterministically in headless Chromium.
        STAGE = "visibility and focus"
        page.evaluate(
            "Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'hidden'});document.dispatchEvent(new Event('visibilitychange'))"
        )
        hidden_count = len(activity_responses)
        page.wait_for_timeout(18000)
        require(len(activity_responses) == hidden_count, "Hidden tab continued polling")
        page.evaluate(
            "Object.defineProperty(document,'visibilityState',{configurable:true,get:()=> 'visible'});document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new Event('focus'))"
        )
        page.wait_for_timeout(4000)
        require(
            len(activity_responses) > hidden_count, "Visibility/focus did not refresh"
        )
        body = page.locator("body").inner_text()
        require(
            private["api_key"] not in body and "key_hash" not in body,
            "Secret exposed in activity UI",
        )
        browser.close()

    rows = [
        r
        for r in select("usage_records", private["user_id"])
        if r["request_id"] == request_id
    ]
    after = snapshot(private["user_id"])
    charges = [
        t for t in after["transactions"] if t["reference_id"] == "usage:" + request_id
    ]
    require(
        len(rows) == len(charges) == 1
        and charges[0]["amount_cents"] == -rows[0]["customer_charge_cents"],
        "Usage/debit not exactly once",
    )
    require(
        before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"]
        == rows[0]["customer_charge_cents"],
        "Unexpected wallet changes during test",
    )
    require(
        after["holds"] == before["holds"]
        and fingerprint(snapshot(ORIGINAL)) == original,
        "Holds or original account changed",
    )
    require(
        not [
            t
            for t in after["transactions"]
            if t["reference_id"] == "usage:" + rejection_id
        ],
        "Rejected request charged",
    )
    print(
        json.dumps(
            {
                "request_id": request_id,
                "rejection_id": rejection_id,
                "input_tokens": rows[0]["input_tokens"],
                "output_tokens": rows[0]["output_tokens"],
                "charge_cents": rows[0]["customer_charge_cents"],
                "before_cents": before["wallet"]["balance_cents"],
                "after_cents": after["wallet"]["balance_cents"],
                "reserved_cents": after["wallet"]["reserved_cents"],
                "auto_refresh": True,
                "filters": True,
                "pagination": True,
                "hidden_pause": True,
                "focus_refresh": True,
                "account_isolation": True,
                "historical_unchanged": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Activity E2E stopped: " + type(exc).__name__
        )
        print("Stage:", STAGE)
        raise SystemExit(1)
