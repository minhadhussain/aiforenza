import { NextResponse } from "next/server";

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { ensureAccountReady, safeDashboardPath } from "@/lib/auth";

export async function GET(request: Request) {
  const requestUrl = new URL(request.url);
  const code = requestUrl.searchParams.get("code");
  const next = safeDashboardPath(requestUrl.searchParams.get("next"));
  const google = requestUrl.searchParams.get("provider") === "google";
  const intent = requestUrl.searchParams.get("intent") === "signup" ? "signup" : "login";
  const redirect = (target: URL) => {
    const response = NextResponse.redirect(target);
    response.headers.set("Cache-Control", "no-store");
    return response;
  };
  const failure = (error: string) => {
    const target = new URL(`/${intent}`, requestUrl.origin);
    target.searchParams.set("error", error);
    target.searchParams.set("next", next);
    return redirect(target);
  };

  if (requestUrl.searchParams.has("error")) {
    return failure(google && requestUrl.searchParams.get("error") === "access_denied" ? "oauth_cancelled" : google ? "oauth_failed" : "confirmation_failed");
  }
  if (!code) return failure(google ? "oauth_failed" : "confirmation_failed");
  try {
    const supabase = await createSupabaseServerClient();
    const { data, error } = await supabase.auth.exchangeCodeForSession(code);
    if (error || !data.session) return failure(google ? "oauth_failed" : "confirmation_failed");
    try {
      // OAuth identities live in Supabase Auth. Reuse the same authenticated
      // profile/wallet bootstrap as password accounts before any deep link.
      await ensureAccountReady(data.session.access_token);
    } catch {
      // Dashboard retries the idempotent setup; never discard a valid session.
      return redirect(new URL("/dashboard", requestUrl.origin));
    }
    return redirect(new URL(next, requestUrl.origin));
  } catch {
    return failure(google ? "oauth_failed" : "confirmation_failed");
  }
}
