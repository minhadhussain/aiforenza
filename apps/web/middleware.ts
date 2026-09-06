import { type NextRequest, NextResponse } from "next/server";

import { refreshAuthSession } from "@/lib/supabase/middleware";

const protectedPrefixes = ["/dashboard"];
const guestOnlyRoutes = new Set(["/login", "/signup"]);

export async function middleware(request: NextRequest) {
  const { response, user } = await refreshAuthSession(request);
  const { pathname } = request.nextUrl;

  if (protectedPrefixes.some((prefix) => pathname.startsWith(prefix)) && !user) {
    const loginUrl = request.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("next", pathname);
    return NextResponse.redirect(loginUrl);
  }

  if (guestOnlyRoutes.has(pathname) && user) {
    const dashboardUrl = request.nextUrl.clone();
    dashboardUrl.pathname = "/dashboard";
    dashboardUrl.search = "";
    return NextResponse.redirect(dashboardUrl);
  }

  return response;
}

export const config = {
  matcher: ["/dashboard/:path*", "/login", "/signup"],
};
