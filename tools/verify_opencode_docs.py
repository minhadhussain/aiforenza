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
        stage = "public_docs"
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
            curl_example = page.get_by_test_id("opencode-curl-example").text_content()
            require(config["provider"]["aiforenza"]["options"]["baseURL"] in curl_example and '"model":"gpt-6-astra"' in curl_example and '"reasoning_effort":"medium"' in curl_example, "curl example does not match the advertised API/model")
            require("read -r -s" in curl_example and "$AI_FORENZA_API_KEY" in curl_example and private["api_key"] not in curl_example, "curl example key handling is incorrect")
            require(list(models["gpt-6-astra"]["variants"]) == ["low", "medium", "high", "xhigh", "max"], "Astra variants mismatch")
            for slug, model in models.items():
                row = page.locator(f'[data-model="{slug}"]')
                expect(row).to_contain_text(model["name"])
                for effort in model.get("variants", {}):
                    expect(row).to_contain_text(effort)
            page.get_by_role("button", name="Copy configuration", exact=True).click()
            expect(page.get_by_role("button", name="Copied", exact=True)).to_be_visible()
            require(json.loads(page.evaluate("navigator.clipboard.readText()")) == config, "Clipboard configuration differs from download")
            stage = "setup_commands"
            config_url = page.get_by_role("link", name="Download opencode.json", exact=True).get_attribute("href")
            for terminal in ("Windows PowerShell", "macOS / Linux"):
                page.get_by_role("button", name=terminal, exact=True).click()
                expect(page.get_by_role("button", name=terminal, exact=True)).to_have_attribute("aria-pressed", "true")
                command = page.get_by_test_id("opencode-install-command").text_content()
                require(config_url in command and "opencode debug paths config" in command, "Setup command does not use the live config or OpenCode path")
                page.get_by_role("button", name="Copy setup command", exact=True).click()
                expect(page.get_by_role("button", name="Command copied", exact=True)).to_be_visible()
                require(page.evaluate("navigator.clipboard.readText()").replace("\r\n", "\n") == command, "Setup command clipboard differs from preview")
                require(private["api_key"] not in command, "Setup command exposes a credential")
            prompt = page.get_by_test_id("opencode-setup-prompt").text_content()
            marker = "CURRENT AI FORENZA CONFIGURATION (JSON)\n"
            require(json.loads(prompt.split(marker, 1)[1]) == config, "Setup prompt differs from current configuration")
            require(page.get_by_role("link", name="Download opencode.json", exact=True).get_attribute("href") in prompt, "Setup prompt configuration source missing")
            page.get_by_role("button", name="Copy setup prompt", exact=True).click()
            expect(page.get_by_role("button", name="Prompt copied", exact=True)).to_be_visible()
            clipboard_prompt = page.evaluate("navigator.clipboard.readText()")
            # Windows clipboard text uses CRLF; HTML text nodes normalize to LF.
            require(clipboard_prompt.replace("\r\n", "\n") == prompt, "Clipboard setup prompt differs from preview")
            page.get_by_text("Preview setup prompt", exact=True).click()
            expect(page.get_by_test_id("opencode-setup-prompt")).to_be_visible()
            stage = "clipboard_failure_fallback"
            page.evaluate("""() => {
                window.__clipboardWrite = navigator.clipboard.writeText;
                navigator.clipboard.writeText = async () => { throw new DOMException('Denied', 'NotAllowedError'); };
            }""")
            try:
                page.get_by_role("button", name="Prompt copied", exact=True).click()
                expect(page.get_by_role("alert").filter(has_text="Clipboard unavailable")).to_be_visible()
                expect(page.get_by_role("button", name="Copy setup prompt", exact=True)).to_be_visible()
                expect(page.get_by_test_id("opencode-setup-prompt")).to_be_visible()
                page.get_by_role("button", name="Copy setup command", exact=True).click()
                expect(page.get_by_role("alert").filter(has_text="Select and copy the setup command below")).to_be_visible()
                expect(page.get_by_test_id("opencode-install-command")).to_be_visible()
            finally:
                page.evaluate("navigator.clipboard.writeText = window.__clipboardWrite; delete window.__clipboardWrite")
            page.get_by_role("button", name="Copy setup prompt", exact=True).click()
            expect(page.get_by_role("button", name="Prompt copied", exact=True)).to_be_visible()
            expect(page.get_by_role("alert").filter(has_text="Clipboard unavailable")).to_have_count(0)
            stage = "configuration_refresh"
            body = page.locator("body").inner_text()
            require("/connect" in body and "Ctrl+T" in body and "gpt-6-astra#high" in body, "Setup/effort instructions missing")
            require(models["gpt-6-astra"]["reasoning"] is True and models["gpt-6-astra"]["options"]["reasoningEffort"] == "medium", "Stale Astra workaround still advertised")
            pattern = "**/v1/public/opencode-config"
            page.route(pattern, lambda route: route.fulfill(status=503, body='{"detail":"fixture unavailable"}', content_type="application/json", headers={"Access-Control-Allow-Origin": args.web}))
            page.get_by_role("button", name="Refresh configuration", exact=True).click()
            expect(page.get_by_role("alert").filter(has_text="Unable to load")).to_be_visible(timeout=30000)
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="Copy setup prompt", exact=True)).to_have_count(0)
            expect(page.get_by_role("button", name="Copy setup command", exact=True)).to_have_count(0)
            page.unroute(pattern)
            page.get_by_role("button", name="Refresh configuration", exact=True).click()
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_be_visible(timeout=30000)
            expect(page.get_by_role("button", name="Copy setup prompt", exact=True)).to_be_visible()
            expect(page.get_by_role("button", name="Copy setup command", exact=True)).to_be_visible()
            stage = "sign_in"
            page.goto(args.web + "/login", wait_until="networkidle")
            page.get_by_label("Email", exact=True).fill(private["email"])
            page.get_by_label("Password", exact=True).fill(private["password"])
            page.get_by_role("button", name="Log in", exact=True).click()
            page.wait_for_url("**/dashboard", timeout=60000)
            stage = "dashboard_docs"
            page.goto(args.web + "/dashboard/docs/opencode", wait_until="networkidle")
            expect(page.get_by_role("link", name="Download opencode.json", exact=True)).to_be_visible(timeout=30000)
            page.get_by_role("button", name="Copy setup prompt", exact=True).click()
            expect(page.get_by_role("button", name="Prompt copied", exact=True)).to_be_visible()
            require(page.evaluate("navigator.clipboard.readText()").replace("\r\n", "\n") == page.get_by_test_id("opencode-setup-prompt").text_content(), "Dashboard setup prompt clipboard mismatch")
            require(private["api_key"] not in page.content(), "Credential exposed in docs")
            print(json.dumps({"public_docs": True, "dashboard_docs": True, "download_and_copy_match": True, "setup_commands_copy_and_preview": True, "setup_prompt_copy_and_preview": True, "prompt_contains_current_config": True, "clipboard_error_recovery": True, "registry_model_ids": list(models), "astra_efforts": list(models["gpt-6-astra"]["variants"]), "no_embedded_credentials": True, "configuration_error_recovery": True}))
        except Exception:
            print(json.dumps({"verification_failed_at": stage}))
            raise
        finally:
            browser.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(str(exc) if type(exc) is RuntimeError else "Documentation verification stopped: " + type(exc).__name__)
        raise SystemExit(1)
