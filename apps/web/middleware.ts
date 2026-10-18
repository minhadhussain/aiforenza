import { type NextRequest, NextResponse } from "next/server";

import { createSecurityPolicy } from "@/lib/security-headers";
import { accountSetupPath, isTemporaryAuthError } from "@/lib/auth";
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
    const nextPath = pathname + request.nextUrl.search;
    try {
      const refreshed = await refreshAuthSession(request, requestHeaders);
      response = refreshed.response;
      if (isTemporaryAuthError(refreshed.error)) {
        const recovery = NextResponse.redirect(new URL(accountSetupPath(nextPath, true), request.url));
        response.cookies.getAll().forEach(cookie => recovery.cookies.set(cookie));
        response = recovery;
      } else if (!refreshed.user) {
        const loginUrl = new URL("/login", request.url);
        loginUrl.searchParams.set("next", nextPath);
        const redirectResponse = NextResponse.redirect(loginUrl);
        response.cookies.getAll().forEach(cookie => redirectResponse.cookies.set(cookie));
        response = redirectResponse;
      }
    } catch {
      // An unavailable auth service is not a logged-out user. Keep cookies and
      // offer recovery outside the protected layout instead of hanging/erroring.
      response = NextResponse.redirect(new URL(accountSetupPath(nextPath, true), request.url));
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
