/** Shared by password forms and server-side OAuth routes. */
export function safeDashboardPath(value?: string | null): string {
  return value && /^\/dashboard(?:\/|\?|$)/.test(value) && !value.includes("\\")
    ? value
    : "/dashboard";
}

export function authErrorMessage(code?: string | string[]): string | undefined {
  switch (code) {
    case "confirmation_failed":
      return "The confirmation link could not be verified. Try signing in, or request a new confirmation email.";
    case "oauth_cancelled":
      return "Google sign-in was cancelled. You can try again or use email and password.";
    case "oauth_failed":
      return "Google sign-in could not be completed. Please try again.";
    case "google_unavailable":
      return "Google sign-in is not enabled yet. Please use email and password for now.";
    default:
      return undefined;
  }
}

export async function ensureAccountReady(accessToken: string): Promise<void> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1";
  const response = await fetch(`${baseUrl}/account/bootstrap`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
    signal: AbortSignal.timeout(20_000),
  });
  if (!response.ok) {
    throw new Error("Account setup is temporarily unavailable. Please try again.");
  }
}
