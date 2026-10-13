const assert = require("node:assert/strict");
const { test } = require("node:test");
const { NextRequest } = require("next/server");
const { load } = require("./helpers.cjs");

const security = load("lib/security-headers.ts");

function directives(policy) {
  return Object.fromEntries(policy.split("; ").map((part) => {
    const [name, ...values] = part.split(" ");
    return [name, values];
  }));
}

test("production policy restricts styles, scripts, and CSS resource exfiltration", () => {
  const { nonce, contentSecurityPolicy } = security.createSecurityPolicy({
    development: false, apiBaseUrl: "https://api.fixture/v1", supabaseUrl: "https://fixture.supabase.co",
  });
  const policy = directives(contentSecurityPolicy);
  assert.equal(Buffer.from(nonce, "base64").length, 16);
  assert.deepEqual(policy["style-src"], ["'self'", `'nonce-${nonce}'`]);
  assert.deepEqual(policy["style-src-attr"], ["'none'"]);
  assert.deepEqual(policy["script-src"], ["'self'", `'nonce-${nonce}'`, "'strict-dynamic'"]);
  assert.deepEqual(policy["img-src"], ["'self'", "data:", "blob:"]);
  assert.deepEqual(policy["font-src"], ["'self'"]);
  assert.deepEqual(policy["connect-src"], ["'self'", "https://api.fixture", "https://fixture.supabase.co"]);
  assert.ok(!contentSecurityPolicy.includes("unsafe-inline"));
  assert.ok(!contentSecurityPolicy.includes("unsafe-eval"));
});

test("development exceptions are limited to Next HMR and do not permit style attributes", () => {
  const policy = directives(security.createSecurityPolicy({ development: true }).contentSecurityPolicy);
  assert.ok(policy["style-src"].includes("'unsafe-inline'"));
  assert.ok(policy["script-src"].includes("'unsafe-eval'"));
  assert.deepEqual(policy["style-src-attr"], ["'none'"]);
  assert.ok(policy["connect-src"].includes("ws://localhost:3000"));
});

test("configuration URLs cannot insert new CSP directives", () => {
  const result = security.createSecurityPolicy({ apiBaseUrl: "https://api.fixture/v1?x=;script-src%20*", development: false });
  assert.deepEqual(directives(result.contentSecurityPolicy)["connect-src"], ["'self'", "https://api.fixture"]);
  for (const apiBaseUrl of ["javascript:alert(1)", "data:text/plain,test", "https://user:password@api.fixture", "https://api.fixture;script-src/", "https://*.fixture/"]) {
    assert.throws(() => security.createSecurityPolicy({ apiBaseUrl }), /Invalid public service origin/);
  }
});

test("middleware replaces attacker nonces and supplies matching policy to Next and the browser", async () => {
  const { middleware } = load("middleware.ts", { "@/lib/supabase/middleware": {} });
  const makeRequest = () => new NextRequest("http://localhost:3000/login", {
    headers: { "x-nonce": "attacker-controlled", "Content-Security-Policy": "script-src * 'unsafe-inline'" },
  });
  const first = await middleware(makeRequest());
  const second = await middleware(makeRequest());
  const policy = first.headers.get("Content-Security-Policy");
  const nonce = first.headers.get("x-middleware-request-x-nonce");
  assert.ok(nonce && nonce !== "attacker-controlled");
  assert.ok(policy.includes(`'nonce-${nonce}'`));
  assert.equal(first.headers.get("x-middleware-request-content-security-policy"), policy);
  assert.notEqual(nonce, second.headers.get("x-middleware-request-x-nonce"));
  assert.equal(first.headers.get("Cache-Control"), "private, no-store");
  assert.equal(first.headers.get("X-Content-Type-Options"), "nosniff");
});

test("session refresh preserves CSP headers and forwards refreshed cookies to server rendering", async () => {
  const request = new NextRequest("http://localhost:3000/dashboard", { headers: { Cookie: "session=expired" } });
  const headers = new Headers(request.headers);
  headers.set("x-nonce", "server-nonce");
  headers.set("Content-Security-Policy", "style-src 'self' 'nonce-server-nonce'");
  const { refreshAuthSession } = load("lib/supabase/middleware.ts", {
    "./config": { getSupabaseConfig: () => ({ url: "https://fixture.supabase.co", anonKey: "fixture" }) },
    "@supabase/ssr": { createServerClient: (_url, _key, options) => ({ auth: {
      getUser: async () => {
        options.cookies.setAll([{ name: "session", value: "refreshed", options: { path: "/" } }]);
        return { data: { user: { id: "fixture" } } };
      },
    } }) },
  });
  const { response } = await refreshAuthSession(request, headers);
  assert.equal(response.headers.get("x-middleware-request-x-nonce"), "server-nonce");
  assert.equal(response.headers.get("x-middleware-request-content-security-policy"), headers.get("Content-Security-Policy"));
  assert.equal(response.headers.get("x-middleware-request-cookie"), "session=refreshed");
  assert.equal(response.cookies.get("session").value, "refreshed");
});

test("API key names render CSS and script payloads as text", () => {
  const React = require("react");
  const { renderToStaticMarkup } = require("react-dom/server");
  const { ApiKeyPanel } = load("components/dashboard/api-key-panel.tsx", {
    "@/components/dashboard/copy-chip": { CopyChip: () => null },
  });
  const payload = '</div><style>body{display:none}</style><img src=x onerror="alert(1)"><script>alert(1)</script>';
  const markup = renderToStaticMarkup(React.createElement(ApiKeyPanel, {
    accessToken: "fixture",
    initialKeys: [{ id: "fixture", name: payload, masked_key: "fixture", created_at: "2026-10-13T00:00:00Z", last_used_at: null, status: "active" }],
  }));
  assert.ok(markup.includes("&lt;style&gt;body{display:none}&lt;/style&gt;"));
  assert.ok(!markup.includes("<style>"));
  assert.ok(!markup.includes("<script>"));
  assert.ok(!markup.includes("<img"));
});
