"""Live catalog/chooser test. --request makes one bounded billed inference call."""

import argparse
import asyncio
import json
from decimal import Decimal
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright, expect

from opencode_live_test import (
    ROOT,
    ORIGINAL,
    state,
    save,
    snapshot,
    fingerprint,
    require,
    select,
)
from app.core.config import settings
from app.repositories.supabase_rest import rest_select
from app.repositories.models import fetch_model_by_slug
from app.models.openai import ChatCompletionRequest
from app.models.usage import UsageMetrics
from app.services.chat_completions import build_provider_payload
from app.services.pricing import calculate_pricing_breakdown
from app.services.usage_records import preflight_spending_details

API = "http://127.0.0.1:8000/v1"
WEB = "http://127.0.0.1:3000"


def catalog():
    return asyncio.run(
        rest_select("/rest/v1/models", {"select": "*", "order": "slug.asc"})
    )


def main(make_request=False):
    private = state()
    rows = catalog()
    astra_rows = [r for r in rows if r["slug"] == "gpt-6-astra"]
    require(len(astra_rows) == 1, "Astra missing or duplicated in registry")
    row = astra_rows[0]
    model = asyncio.run(fetch_model_by_slug("gpt-6-astra"))
    require(
        model
        and model.enabled
        and model.provider.lower() == "azure"
        and model.provider_model_id == "gpt-6-astra",
        "Incorrect Astra routing or enabled state",
    )
    require(
        settings.azure_endpoint and settings.azure_api_key,
        "Configured Azure route required",
    )
    before = snapshot(private["user_id"])
    original = fingerprint(snapshot(ORIGINAL))
    with httpx.Client(timeout=60) as client:
        inventory = client.get(
            settings.azure_endpoint.rstrip("/") + "/models",
            headers={"api-key": settings.azure_api_key},
        )
        require(
            inventory.status_code == 200
            and any(
                m["id"] == model.provider_model_id for m in inventory.json()["data"]
            ),
            "Astra absent from configured Azure inventory",
        )
        login = client.post(
            settings.supabase_url.rstrip("/") + "/auth/v1/token?grant_type=password",
            headers={"apikey": settings.supabase_anon_key},
            json={"email": private["email"], "password": private["password"]},
        )
        require(login.status_code == 200, "Test dashboard sign-in failed")
        auth = {"Authorization": "Bearer " + login.json()["access_token"]}
        public = client.get(
            API + "/models", headers={"Authorization": "Bearer " + private["api_key"]}
        )
        dashboard = client.get(API + "/dashboard/models", headers=auth)
        public_catalog = client.get(API + "/public/models")
        require(public_catalog.status_code == 200, "Public catalog unavailable")
        require(public.status_code == dashboard.status_code == 200, "Model APIs failed")
        public_ids = [m["id"] for m in public.json()["data"]]
        dashboard_ids = [m["slug"] for m in dashboard.json()["data"]]
        require(
            {m["slug"] for m in public_catalog.json()["data"]} == set(dashboard_ids),
            "Public catalog differs",
        )
        require(
            set(public_ids) == set(dashboard_ids)
            and public_ids.count("gpt-6-astra") == 1,
            "Model API parity failed",
        )
    print(
        json.dumps(
            {
                "astra_configuration": {
                    k: row[k]
                    for k in (
                        "id",
                        "slug",
                        "display_name",
                        "provider",
                        "provider_model_id",
                        "enabled",
                        "pricing_verified",
                        "input_price_per_million",
                        "output_price_per_million",
                        "cached_input_price_per_million",
                        "discount_percent",
                    )
                },
                "api_models": public_ids,
                "azure_inventory_verified": True,
            }
        ),
        flush=True,
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(WEB + "/login", wait_until="networkidle")
        page.get_by_label("Email", exact=True).fill(private["email"])
        page.get_by_label("Password", exact=True).fill(private["password"])
        page.get_by_role("button", name="Log in", exact=True).click()
        page.wait_for_url("**/dashboard", wait_until="domcontentloaded", timeout=60000)
        expect(page.get_by_role("combobox", name="AI Forenza model")).to_have_count(0)
        expect(page.get_by_test_id("all-model-access")).to_contain_text(
            "No model activation or selection is required"
        )
        selected = model.slug
        page.get_by_role("button", name="Refresh dashboard", exact=True).click()
        expect(
            page.get_by_role("button", name="Refresh dashboard", exact=True)
        ).to_be_enabled(timeout=60000)
        expect(page.get_by_role("combobox", name="AI Forenza model")).to_have_count(0)
        page.goto(WEB + "/dashboard/models", wait_until="networkidle")
        expect(page.get_by_text("GPT-6 Astra", exact=True)).to_be_visible()
        page.goto(WEB + "/models", wait_until="networkidle")
        astra_button = page.get_by_role("button", name="GPT-6 Astra", exact=False)
        expect(astra_button).to_be_visible(timeout=30000)
        astra_button.click()
        expect(
            page.get_by_role("heading", name="GPT-6 Astra", exact=True)
        ).to_be_visible()
        page.get_by_role("textbox", name="Search models").fill("gpt-6-astra")
        expect(astra_button).to_be_visible()
        page.get_by_role("textbox", name="Search models").fill("no-such-model-fixture")
        expect(
            page.get_by_text("No models match your search.", exact=True)
        ).to_be_visible()
        page.get_by_role("textbox", name="Search models").fill("")
        for m in dashboard.json()["data"]:
            expect(
                page.get_by_role("button", name=m["display_name"], exact=False)
            ).to_be_visible()
        browser.close()
    print(
        json.dumps(
            {
                "no_dashboard_activation_or_selector": True,
                "same_key_api_models": public_ids,
                "dashboard_models_page": True,
                "public_chooser_and_search": True,
            }
        ),
        flush=True,
    )
    if make_request:
        require(
            not private.get("astra_restore_verification_started"),
            "Astra test already attempted; avoid spending again",
        )
        request = ChatCompletionRequest(
            model=selected,
            messages=[{"role": "user", "content": "Reply OK only."}],
            max_completion_tokens=32,
        )
        details = preflight_spending_details(request, model)
        require(
            details["customer_charge_cents"] <= 2
            and before["wallet"]["available_balance_cents"]
            >= details["customer_charge_cents"],
            "Test spending guard failed",
        )
        route = build_provider_payload(request, model, "req_test_routing")
        require(route["model"] == "gpt-6-astra", "Selected model routed incorrectly")
        private["astra_restore_verification_started"] = True
        save(private)
        with httpx.Client(timeout=150) as client:
            response = client.post(
                API + "/chat/completions",
                headers={"Authorization": "Bearer " + private["api_key"]},
                json=request.model_dump(exclude_none=True),
            )
        require(
            response.status_code == 200 and response.json().get("model") == selected,
            "Astra request failed; inspect holds before retry",
        )
        require(
            bool(response.json()["choices"][0]["message"].get("content")),
            "Astra returned no text",
        )
        request_id = response.headers["x-request-id"]
        usage = [
            r
            for r in select("usage_records", private["user_id"])
            if r["request_id"] == request_id
        ]
        after = snapshot(private["user_id"])
        charges = [
            t
            for t in after["transactions"]
            if t["reference_id"] == "usage:" + request_id
        ]
        require(len(usage) == len(charges) == 1, "Usage/charge not exactly once")
        record = usage[0]
        require(
            record["model_id"] == row["id"]
            and record["api_key_id"] == private["key_id"]
            and record["status"] == "completed",
            "Usage identity mismatch",
        )
        expected = calculate_pricing_breakdown(
            model,
            UsageMetrics(
                input_tokens=record["input_tokens"],
                output_tokens=record["output_tokens"],
                cached_input_tokens=record["cached_input_tokens"],
            ),
        )
        require(
            record["customer_charge_cents"] == expected.customer_charge_cents
            and charges[0]["amount_cents"] == -expected.customer_charge_cents,
            "Billing mismatch",
        )
        require(
            before["wallet"]["balance_cents"] - after["wallet"]["balance_cents"]
            == expected.customer_charge_cents,
            "Wallet delta mismatch",
        )
        require(
            after["holds"] == before["holds"],
            "Existing holds altered or new hold leaked",
        )
        report = {
            "request_id": request_id,
            "model": selected,
            "http_status": 200,
            "provider": model.provider,
            "provider_model_id": route["model"],
            "input_tokens": record["input_tokens"],
            "output_tokens": record["output_tokens"],
            "reference_cents": expected.reference_charge_cents,
            "customer_cents": expected.customer_charge_cents,
            "before_cents": before["wallet"]["balance_cents"],
            "after_cents": after["wallet"]["balance_cents"],
            "reserved_cents": after["wallet"]["reserved_cents"],
            "existing_holds_preserved": True,
        }
        private["astra_restore_verification"] = report
        save(private)
        print(json.dumps(report, indent=2))
    require(catalog() == rows, "Model registry was modified")
    require(
        fingerprint(snapshot(ORIGINAL)) == original, "Original wallet/holds modified"
    )
    print("Full model registry and original account unchanged")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", action="store_true")
    args = parser.parse_args()
    try:
        main(args.request)
    except Exception as exc:
        print(
            str(exc)
            if type(exc) is RuntimeError
            else "Astra check stopped: " + type(exc).__name__
        )
        raise SystemExit(1)
