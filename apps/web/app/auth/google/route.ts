import { NextResponse } from "next/server";

import { safeDashboardPath } from "@/lib/auth";
import { getSupabaseConfig } from "@/lib/supabase/config";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function GET(request: Request) {
  const current = new URL(request.url);
  const intent = current.searchParams.get("intent") === "signup" ? "signup" : "login";
  const next = safeDashboardPath(current.searchParams.get("next"));
  const failure = (code: string) => {
    const target = new URL(`/${intent}`, current.origin);
    target.searchParams.set("error", code);
    target.searchParams.set("next", next);
    const response = NextResponse.redirect(target);
    response.headers.set("Cache-Control", "no-store");
    return response;
  };

  try {
    // The hosted Supabase configuration is authoritative; do not send users to
    // an opaque provider-disabled error page or infer readiness from the UI.
    const { url, anonKey } = getSupabaseConfig();
    const settings = await fetch(`${url}/auth/v1/settings`, {
      headers: { apikey: anonKey },
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (!settings.ok) return failure("oauth_failed");
    if ((await settings.json()).external?.google !== true) return failure("google_unavailable");

    const callback = new URL("/auth/callback", current.origin);
    callback.searchParams.set("next", next);
    callback.searchParams.set("provider", "google");
    callback.searchParams.set("intent", intent);
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: callback.toString(),
        queryParams: { prompt: "select_account" },
        skipBrowserRedirect: true,
      },
    });
    if (error || !data.url) return failure("oauth_failed");
    const response = NextResponse.redirect(data.url);
    response.headers.set("Cache-Control", "no-store");
    return response;
  } catch {
    return failure("oauth_failed");
  }
}
