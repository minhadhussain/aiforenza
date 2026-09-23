const assert = require("node:assert/strict");
const { test } = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const ts = require("typescript");

// Execute the actual route/helper source with only external I/O substituted.
// Type-checking of that same source is also performed by next build / tsc.
function load(relative, imports = {}, fetch = async () => new Response(null, { status: 200 })) {
  const source = fs.readFileSync(path.join(__dirname, "..", relative), "utf8");
  const compiled = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const module = { exports: {} };
  vm.runInNewContext(compiled, {
    module, exports: module.exports,
    require: (name) => imports[name] ?? require(name),
    URL, URLSearchParams, Request, Response, Headers, AbortSignal, fetch,
    process: { env: { NEXT_PUBLIC_API_BASE_URL: "http://api.fixture/v1" } },
  }, { filename: relative });
  return module.exports;
}

const auth = load("lib/auth.ts");
const config = { getSupabaseConfig: () => ({ url: "https://fixture.supabase.co", anonKey: "public-fixture-key" }) };

test("the actual Supabase SSR SDK creates a PKCE challenge and verifier cookie", async () => {
  const { createServerClient } = require("@supabase/ssr");
  const cookies = new Map();
  const supabase = createServerClient("https://fixture.supabase.co", "public-fixture-key", {
    cookies: {
      getAll: () => [...cookies].map(([name, value]) => ({ name, value })),
      setAll: (updates) => updates.forEach(({ name, value }) => cookies.set(name, value)),
    },
  });
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: { redirectTo: "http://localhost:3000/auth/callback", skipBrowserRedirect: true },
  });
  assert.equal(error, null);
  const target = new URL(data.url);
  assert.equal(target.origin, "https://fixture.supabase.co");
  assert.equal(target.searchParams.get("provider"), "google");
  assert.equal(target.searchParams.get("code_challenge_method"), "s256");
  assert.ok(target.searchParams.get("code_challenge"));
  assert.ok([...cookies.keys()].some((name) => name.includes("code-verifier")));
});

test("auth redirects accept dashboard paths and reject external paths", () => {
  for (const value of [null, "//evil.invalid", "https://evil.invalid", "/dashboard\\evil", "/dashboard-other"]) {
    assert.equal(auth.safeDashboardPath(value), "/dashboard");
  }
  assert.equal(auth.safeDashboardPath("/dashboard/api-keys?tab=active"), "/dashboard/api-keys?tab=active");
  assert.equal(auth.authErrorMessage("PRIVATE_UNTRUSTED_ERROR"), undefined);
});

test("account setup sends only the bearer credential to the existing backend", async () => {
  let seen;
  const helper = load("lib/auth.ts", {}, async (url, options) => {
    seen = { url, options };
    return new Response('{"ready":true}');
  });
  await helper.ensureAccountReady("private-session-fixture");
  assert.equal(seen.url, "http://api.fixture/v1/account/bootstrap");
  assert.equal(seen.options.method, "POST");
  assert.equal(seen.options.headers.Authorization, "Bearer private-session-fixture");
  assert.equal(seen.options.body, undefined);
});

test("account setup failures do not expose upstream error bodies", async () => {
  const helper = load("lib/auth.ts", {}, async () => new Response("PRIVATE_DATABASE_ERROR", { status: 503 }));
  await assert.rejects(helper.ensureAccountReady("session"), /Account setup is temporarily unavailable/);
});

test("Google signup starts the Supabase OAuth/PKCE flow with a safe callback", async () => {
  let args;
  const route = load("app/auth/google/route.ts", {
    "@/lib/auth": auth,
    "@/lib/supabase/config": config,
    "@/lib/supabase/server": { createSupabaseServerClient: async () => ({ auth: {
      signInWithOAuth: async (input) => {
        args = input;
        return { data: { url: "https://fixture.supabase.co/auth/v1/authorize?provider=google&code_challenge=fixture" }, error: null };
      },
    } }) },
  }, async () => Response.json({ external: { google: true } }));
  const result = await route.GET(new Request("http://localhost:3000/auth/google?intent=signup&next=/dashboard/api-keys"));
  assert.equal(result.status, 307);
  assert.equal(result.headers.get("Cache-Control"), "no-store");
  assert.match(result.headers.get("Location"), /^https:\/\/fixture.supabase.co\/auth\/v1\/authorize/);
  assert.equal(args.provider, "google");
  assert.equal(args.options.skipBrowserRedirect, true);
  assert.equal(args.options.queryParams.prompt, "select_account");
  const callback = new URL(args.options.redirectTo);
  assert.equal(callback.origin, "http://localhost:3000");
  assert.equal(callback.pathname, "/auth/callback");
  assert.equal(callback.searchParams.get("next"), "/dashboard/api-keys");
  assert.equal(callback.searchParams.get("intent"), "signup");
});

test("disabled Google returns a clear signup error without starting OAuth", async () => {
  const route = load("app/auth/google/route.ts", {
    "@/lib/auth": auth,
    "@/lib/supabase/config": config,
    "@/lib/supabase/server": { createSupabaseServerClient: async () => { throw new Error("Must not start OAuth"); } },
  }, async () => Response.json({ external: { google: false } }));
  const result = await route.GET(new Request("http://localhost:3000/auth/google?intent=signup&next=https://evil.invalid"));
  const target = new URL(result.headers.get("Location"));
  assert.equal(target.pathname, "/signup");
  assert.equal(target.searchParams.get("error"), "google_unavailable");
  assert.equal(target.searchParams.get("next"), "/dashboard");
});

test("OAuth startup network errors return a safe retryable message", async () => {
  const route = load("app/auth/google/route.ts", { "@/lib/auth": auth, "@/lib/supabase/config": config, "@/lib/supabase/server": {} }, async () => { throw new Error("PRIVATE_CONFIG"); });
  const result = await route.GET(new Request("http://localhost:3000/auth/google"));
  assert.equal(new URL(result.headers.get("Location")).searchParams.get("error"), "oauth_failed");
  assert.ok(!result.headers.get("Location").includes("PRIVATE"));
});

function callback(exchange, setup = async () => {}) {
  return load("app/auth/callback/route.ts", {
    "@/lib/auth": { ...auth, ensureAccountReady: setup },
    "@/lib/supabase/server": { createSupabaseServerClient: async () => ({ auth: { exchangeCodeForSession: exchange } }) },
  });
}

test("OAuth callback exchanges the code then bootstraps the verified session", async () => {
  const calls = [];
  const route = callback(async (code) => {
    calls.push(code);
    return { data: { session: { access_token: "session-fixture" } }, error: null };
  }, async (token) => calls.push(token));
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?provider=google&code=code-fixture&next=/dashboard/api-keys"));
  assert.deepEqual(calls, ["code-fixture", "session-fixture"]);
  assert.equal(response.headers.get("Location"), "http://localhost:3000/dashboard/api-keys");
  assert.equal(response.headers.get("Cache-Control"), "no-store");
});

test("cancelled Google signup does not exchange a code or create an account", async () => {
  const route = callback(async () => { throw new Error("Must not exchange"); });
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?provider=google&intent=signup&error=access_denied&error_description=PRIVATE_TEXT"));
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.pathname, "/signup");
  assert.equal(target.searchParams.get("error"), "oauth_cancelled");
  assert.ok(!target.toString().includes("PRIVATE"));
});

test("bad OAuth codes return safe errors and reject external return URLs", async () => {
  const route = callback(async () => ({ data: { session: null }, error: { message: "PRIVATE_TOKEN_ERROR" } }));
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?provider=google&code=bad&next=//evil.invalid"));
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.origin, "http://localhost:3000");
  assert.equal(target.searchParams.get("error"), "oauth_failed");
  assert.equal(target.searchParams.get("next"), "/dashboard");
});

test("valid sessions retry account setup through dashboard after a backend outage", async () => {
  const route = callback(async () => ({ data: { session: { access_token: "fixture" } }, error: null }), async () => { throw new Error("Unavailable"); });
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?code=fixture&next=/dashboard/api-keys"));
  assert.equal(response.headers.get("Location"), "http://localhost:3000/dashboard");
});
