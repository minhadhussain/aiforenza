"""Live public/dashboard documentation, downloads, and clipboard checks."""

import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from opencode_live_test import state, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", default="http://127.0.0.1:3000")
    args = parser.parse_args()
    private = state()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(permissions=["clipboard-read", "clipboard-write"])
        page = context.new_page()
        try:
            page.goto(args.web + "/docs/opencode", wait_until="networkidle", timeout=60000)
            expect(page.get_by_role("heading", name="OpenCode setup and reasoning efforts", exact=True)).to_be_visible()
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_be_visible(timeout=30000)
            with page.expect_download() as pending:
                page.get_by_role("link", name="Download opencode.json", exact=True).click()
            download = pending.value
            require(download.suggested_filename == "opencode.json", "Unexpected download filename")
            config = json.loads(Path(download.path()).read_text(encoding="utf-8"))
            require("apiKey" not in json.dumps(config), "Configuration includes a credential override")
            models = config["provider"]["aiforenza"]["models"]
            require(list(models["gpt-6-astra"]["variants"]) == ["low", "medium", "high", "xhigh", "max"], "Astra variants mismatch")
            for slug, model in models.items():
                row = page.locator(f'[data-model="{slug}"]')
                expect(row).to_contain_text(model["name"])
                for effort in model.get("variants", {}):
                    expect(row).to_contain_text(effort)
            page.get_by_role("button", name="Copy configuration", exact=True).click()
            expect(page.get_by_role("button", name="Copied", exact=True)).to_be_visible()
            require(json.loads(page.evaluate("navigator.clipboard.readText()")) == config, "Clipboard configuration differs from download")
            body = page.locator("body").inner_text()
            require("/connect" in body and "Ctrl+T" in body and "--variant high" in body, "Setup/effort instructions missing")
            require(models["gpt-6-astra"]["reasoning"] is True and models["gpt-6-astra"]["options"]["reasoningEffort"] == "medium", "Stale Astra workaround still advertised")
            pattern = "**/v1/public/opencode-config"
            page.route(pattern, lambda route: route.fulfill(status=503, body='{"detail":"fixture unavailable"}', content_type="application/json", headers={"Access-Control-Allow-Origin": args.web}))
            page.get_by_role("button", name="Refresh configuration", exact=True).click()
            expect(page.get_by_role("alert").filter(has_text="Unable to load")).to_be_visible(timeout=30000)
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_have_count(0)
            page.unroute(pattern)
            page.get_by_role("button", name="Refresh configuration", exact=True).click()
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_be_visible(timeout=30000)
            page.goto(args.web + "/login", wait_until="networkidle")
            page.get_by_label("Email", exact=True).fill(private["email"])
            page.get_by_label("Password", exact=True).fill(private["password"])
            page.get_by_role("button", name="Log in", exact=True).click()
            page.wait_for_url("**/dashboard", timeout=60000)
            page.goto(args.web + "/dashboard/docs/opencode", wait_until="networkidle")
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_be_visible(timeout=30000)
            require(private["api_key"] not in page.content(), "Credential exposed in docs")
            print(json.dumps({"public_docs": True, "dashboard_docs": True, "download_and_copy_match": True, "registry_model_ids": list(models), "astra_efforts": list(models["gpt-6-astra"]["variants"]), "no_embedded_credentials": True, "configuration_error_recovery": True}))
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Documentation verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
