const assert = require("node:assert/strict");
const { test } = require("node:test");
const { load } = require("./helpers.cjs");

const auth = load("lib/auth.ts");
const config = { getSupabaseConfig: () => ({ url: "https://fixture.supabase.co", anonKey: "public-fixture-key" }) };

test("public auth pages open even when the saved-session service is unavailable", async () => {
  const { NextRequest } = require("next/server");
  const { middleware } = load("middleware.ts", {
    "@/lib/supabase/middleware": {
      refreshAuthSession: async () => { throw new Error("Session service is unavailable"); },
    },
  });
  for (const route of ["/login", "/signup"]) {
    const request = new NextRequest(`http://localhost:3000${route}`, {
      headers: { Cookie: "sb-fixture-auth-token=expired-session" },
    });
    const response = await middleware(request);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get("Location"), null);
  }
});

test("protected navigation still checks the session and clears stale cookies on redirect", async () => {
  const { NextRequest, NextResponse } = require("next/server");
  let checked = false;
  const { middleware } = load("middleware.ts", {
    "@/lib/supabase/middleware": {
      refreshAuthSession: async () => {
        checked = true;
        const response = NextResponse.next();
        response.cookies.set("sb-fixture-auth-token", "", { maxAge: 0 });
        return { response, user: null };
      },
    },
  });
  const response = await middleware(new NextRequest("http://localhost:3000/dashboard/api-keys"));
  assert.equal(checked, true);
  assert.equal(response.status, 307);
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.pathname, "/login");
  assert.equal(target.searchParams.get("next"), "/dashboard/api-keys");
  assert.equal(response.cookies.get("sb-fixture-auth-token").maxAge, 0);
});

test("authenticated dashboard navigation preserves refreshed session cookies", async () => {
  const { NextRequest, NextResponse } = require("next/server");
  const refreshed = NextResponse.next();
  refreshed.cookies.set("sb-fixture-auth-token", "refreshed-session");
  const { middleware } = load("middleware.ts", {
    "@/lib/supabase/middleware": {
      refreshAuthSession: async () => ({ response: refreshed, user: { id: "fixture" } }),
    },
  });
  const response = await middleware(new NextRequest("http://localhost:3000/dashboard"));
  assert.equal(response, refreshed);
  assert.equal(response.headers.get("Location"), null);
  assert.equal(response.cookies.get("sb-fixture-auth-token").value, "refreshed-session");
});

test("temporary session failures recover outside the dashboard without losing the return path", async () => {
  const { NextRequest, NextResponse } = require("next/server");
  for (const throws of [false, true]) {
    const refreshed = NextResponse.next();
    refreshed.cookies.set("sb-fixture-auth-token", "refreshed-session");
    const { middleware } = load("middleware.ts", {
      "@/lib/supabase/middleware": {
        refreshAuthSession: async () => {
          if (throws) throw new DOMException("Timeout", "TimeoutError");
          return { response: refreshed, user: null, error: { name: "AuthRetryableFetchError", status: 0 } };
        },
      },
    });
    const result = await middleware(new NextRequest("http://localhost:3000/dashboard/api-keys?tab=active"));
    const target = new URL(result.headers.get("Location"));
    assert.equal(target.pathname, "/auth/complete");
    assert.equal(target.searchParams.get("next"), "/dashboard/api-keys?tab=active");
    assert.equal(target.searchParams.get("retry"), "1");
    assert.match(result.headers.get("Cache-Control"), /no-store/);
    if (!throws) assert.equal(result.cookies.get("sb-fixture-auth-token").value, "refreshed-session");
  }
});

test("the recovery page stays reachable when the session service is down", async () => {
  const { NextRequest } = require("next/server");
  const { middleware } = load("middleware.ts", {
    "@/lib/supabase/middleware": { refreshAuthSession: async () => { throw new Error("Must not check session"); } },
  });
  const result = await middleware(new NextRequest("http://localhost:3000/auth/complete?retry=1"));
  assert.equal(result.status, 200);
  assert.equal(result.headers.get("Location"), null);
});

test("auth requests get a deadline while retaining caller cancellation", async () => {
  let signal;
  const { authFetch } = load("lib/supabase/fetch.ts", {}, async (_url, options) => {
    signal = options.signal;
    return new Response(null);
  });
  await authFetch("https://fixture.supabase.co/auth/v1/user");
  assert.ok(signal instanceof AbortSignal);
  const caller = new AbortController();
  await authFetch(new Request("https://fixture.supabase.co/auth/v1/user", { signal: caller.signal }));
  assert.notEqual(signal, caller.signal);
  caller.abort();
  assert.equal(signal.aborted, true);
});

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

test("OAuth callback commits the session then opens visible setup before a dashboard deep link", async () => {
  const calls = [];
  const route = callback(async (code) => {
    calls.push(code);
    return { data: { session: { access_token: "session-fixture" } }, error: null };
  }, async (token) => calls.push(token));
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?provider=google&code=code-fixture&next=/dashboard/api-keys"));
  assert.deepEqual(calls, ["code-fixture"]);
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.pathname, "/auth/complete");
  assert.equal(target.searchParams.get("next"), "/dashboard/api-keys");
  assert.ok(!target.toString().includes("session-fixture"));
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

test("a backend outage cannot block the successful OAuth redirect", async () => {
  const route = callback(async () => ({ data: { session: { access_token: "fixture" } }, error: null }), async () => { throw new Error("Unavailable"); });
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?code=fixture&next=/dashboard/api-keys"));
  const target = new URL(response.headers.get("Location"));
  assert.equal(target.pathname, "/auth/complete");
  assert.equal(target.searchParams.get("next"), "/dashboard/api-keys");
});

test("a new provider session persists chunked SSR cookies through the OAuth callback", async () => {
  const { createServerClient } = require("@supabase/ssr");
  const cookies = new Map();
  const session = {
    access_token: "access-token-fixture",
    refresh_token: "refresh-token-fixture",
    provider_token: "provider-token-fixture".repeat(200),
    token_type: "bearer",
    expires_in: 3600,
    user: { id: "user-fixture", email: "fixture@example.invalid", user_metadata: { full_name: "New User" } },
  };
  const client = createServerClient("https://fixture.supabase.co", "public-fixture-key", {
    global: { fetch: async () => Response.json(session) },
    cookies: {
      getAll: () => [...cookies].map(([name, value]) => ({ name, value })),
      setAll: updates => updates.forEach(({ name, value, options }) => {
        if (options.maxAge === 0) cookies.delete(name);
        else cookies.set(name, value);
      }),
    },
  });
  await client.auth.signInWithOAuth({ provider: "google", options: { skipBrowserRedirect: true } });
  const route = load("app/auth/callback/route.ts", {
    "@/lib/supabase/server": { createSupabaseServerClient: async () => client },
  });
  const response = await route.GET(new Request("http://localhost:3000/auth/callback?provider=google&intent=signup&code=fixture"));
  assert.equal(new URL(response.headers.get("Location")).pathname, "/auth/complete");
  assert.ok([...cookies.keys()].filter(name => /auth-token\.\d+$/.test(name)).length > 1);
  assert.equal([...cookies.keys()].some(name => name.includes("code-verifier")), false);
});
