import { type NextRequest, NextResponse } from "next/server";

import { createSecurityPolicy } from "@/lib/security-headers";
import { refreshAuthSession } from "@/lib/supabase/middleware";

const protectedPrefixes = ["/dashboard"];

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const { nonce, contentSecurityPolicy } = createSecurityPolicy();
  const requestHeaders = new Headers(request.headers);
  // Replace any client-supplied nonce/policy before Next generates framework tags.
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", contentSecurityPolicy);
  let response = NextResponse.next({ request: { headers: requestHeaders } });

  // Public auth pages remain independent of saved-session refresh/network I/O.
  if (protectedPrefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`))) {
    const refreshed = await refreshAuthSession(request, requestHeaders);
    response = refreshed.response;
    if (!refreshed.user) {
      const loginUrl = request.nextUrl.clone();
      loginUrl.pathname = "/login";
      loginUrl.searchParams.set("next", pathname);
      const redirectResponse = NextResponse.redirect(loginUrl);
      response.cookies.getAll().forEach(cookie => redirectResponse.cookies.set(cookie));
      response = redirectResponse;
    }
  }

  response.headers.set("Content-Security-Policy", contentSecurityPolicy);
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("Referrer-Policy", "strict-origin-when-cross-origin");
  // A nonce-bearing document must never be reused across requests by a cache.
  response.headers.set("Cache-Control", "private, no-store");
  return response;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
