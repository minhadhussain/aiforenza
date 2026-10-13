"""Browser CSP checks against a local production build, using synthetic API data.

Run next build/start on port 3100, then: python tools/verify_injection_prevention.py
No accounts, keys, database rows, or paid inference are created by this check.
"""

import argparse
import json
import re

from playwright.sync_api import expect, sync_playwright


def check(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(base_url):
    payload = '</div><style id="injected-style">body{display:none}</style><img src="https://css-probe.invalid/leak">'
    model = {
        "slug": "fixture-model", "display_name": payload, "provider": "fixture",
        "customer_input_price_per_million": 1, "customer_output_price_per_million": 2,
        "discount_percent": 40,
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            context.route("**/v1/public/models", lambda route: route.fulfill(json={"data": [model]}))
            outbound = []

            def unexpected_request(route):
                outbound.append(True)
                route.fulfill(status=200, body="")

            context.route("https://css-probe.invalid/**", unexpected_request)
            context.add_init_script("""window.__cspViolations = [];
                document.addEventListener('securitypolicyviolation', event => {
                  window.__cspViolations.push(event.effectiveDirective);
                });""")
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda _: errors.append("browser_error"))
            nonces = []
            for path in ("/", "/login", "/signup", "/docs", "/docs/introduction", "/models", "/pricing"):
                response = page.goto(base_url + path, wait_until="networkidle", timeout=60000)
                check(response.status == 200, "Page failed: " + path)
                policy = response.header_value("content-security-policy") or ""
                check("style-src-attr 'none'" in policy and "'unsafe-inline'" not in policy and "'unsafe-eval'" not in policy, "Expected an enforced production CSP: " + path)
                nonce = page.locator("script[nonce]").first.evaluate("script => script.nonce")
                check(nonce and "'nonce-" + nonce + "'" in policy, "Framework nonce differs from response policy: " + path)
                nonces.append(nonce)
                expect(page.locator("main")).to_be_visible()
                check(not page.evaluate("window.__cspViolations"), "Legitimate page hit a CSP violation: " + path)
                if path in ("/login", "/signup"):
                    expect(page.get_by_label("Email", exact=True)).to_be_visible()
                    expect(page.get_by_role("button", name="Continue with Google", exact=True)).to_be_visible()
                print(json.dumps({"path": path, "csp": "enforced", "framework_nonce_valid": True}), flush=True)
            check(len(set(nonces)) == len(nonces), "Nonce was reused across pages")

            page.goto(base_url + "/", wait_until="networkidle")
            page.get_by_role("button", name="JavaScript", exact=True).click()
            expect(page.get_by_role("heading", name="JavaScript", exact=True)).to_be_visible()
            page.locator("header").get_by_role("link", name="Log in", exact=True).click()
            expect(page.get_by_label("Email", exact=True)).to_be_visible()
            page.get_by_role("link", name="Create an account", exact=True).click()
            expect(page.get_by_role("heading", name="Create your account", exact=True)).to_be_visible()
            print(json.dumps({"hydration": True, "login_signup_navigation": True}), flush=True)

            page.goto(base_url + "/models", wait_until="networkidle")
            expect(page.get_by_role("button").filter(has_text=payload)).to_have_count(1)
            check(page.locator("#injected-style").count() == 0, "API text became a style element")
            check(page.locator('img[src*="css-probe.invalid"]').count() == 0, "API text became an image element")
            page.get_by_label("Search models", exact=True).fill("fixture-model")
            expect(page.get_by_role("button").filter(has_text=payload)).to_have_count(1)
            print(json.dumps({"hostile_api_text_escaped": True, "model_search": True}), flush=True)

            # Test parser-inserted scripts, as in an HTML injection. A script
            # appended by already-trusted JS is intentionally allowed by strict-dynamic.
            def inject_script_fixture(route):
                response = route.fetch()
                nonce = re.search(r"'nonce-([^']+)'", response.headers["content-security-policy"]).group(1)
                injected = '<script>window.__unapprovedParserScript = true;</script>'
                injected += '<script nonce="' + nonce + '">window.__approvedParserScript = true;</script>'
                route.fulfill(response=response, body=response.text().replace("</head>", injected + "</head>", 1))

            page.route(base_url + "/login", inject_script_fixture)
            page.goto(base_url + "/login", wait_until="networkidle")
            check(page.evaluate("window.__approvedParserScript === true && !window.__unapprovedParserScript"), "Parser-inserted script policy failed")
            check("script-src-elem" in page.evaluate("window.__cspViolations"), "Missing script rejection event")

            results = page.evaluate("""async () => {
              const probe = document.createElement('div');
              probe.id = 'csp-probe';
              probe.textContent = 'CSP probe';
              document.body.append(probe);
              const before = getComputedStyle(probe).color;
              probe.setAttribute('style', 'color:rgb(12,34,56)');
              const attributeBlocked = getComputedStyle(probe).color === before;
              const inline = document.createElement('style');
              inline.textContent = '#csp-probe{color:rgb(12,34,56)}';
              document.head.append(inline);
              const inlineBlocked = getComputedStyle(probe).color === before;
              const trusted = document.createElement('style');
              trusted.nonce = document.querySelector('script[nonce]').nonce;
              trusted.textContent = '#csp-probe{background-color:rgb(34,56,78);background-image:url(https://css-probe.invalid/image)}';
              document.head.append(trusted);
              const trustedAllowed = getComputedStyle(probe).backgroundColor === 'rgb(34, 56, 78)';
              const link = document.createElement('link');
              link.rel = 'stylesheet';
              link.href = 'https://css-probe.invalid/stylesheet.css';
              document.head.append(link);
              await new Promise(resolve => setTimeout(resolve, 300));
              return { attributeBlocked, inlineBlocked, trustedAllowed,
                violations: window.__cspViolations };
            }""")
            check(all(results[key] for key in ("attributeBlocked", "inlineBlocked", "trustedAllowed")), "Browser did not enforce injection boundaries")
            check("style-src-attr" in results["violations"] and "style-src-elem" in results["violations"] and "img-src" in results["violations"], "Expected browser rejection events missing")
            check(not outbound, "Injected CSS caused an outbound request")
            check(not errors, "Browser runtime errors occurred")
            print(json.dumps({"inline_style_blocked": True, "style_attribute_blocked": True, "external_css_blocked": True, "css_image_exfiltration_blocked": True, "unapproved_script_blocked": True, "nonce_style_allowed": True, "browser_errors": 0}), flush=True)
        finally:
            browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:3100")
    args = parser.parse_args()
    try:
        verify(args.url.rstrip("/"))
    except Exception as error:
        print(str(error) if type(error) is RuntimeError else "Browser verification stopped: " + type(error).__name__)
        raise SystemExit(1)
