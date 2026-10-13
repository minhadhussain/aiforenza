type SecurityPolicyOptions = {
  development?: boolean;
  apiBaseUrl?: string;
  supabaseUrl?: string;
};

function configuredOrigin(value: string): string {
  const url = new URL(value);
  if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || /[;'"\s*]/.test(url.origin)) {
    throw new Error("Invalid public service origin.");
  }
  // Only configuration-owned origins enter the policy, never request headers or URLs.
  return url.origin;
}

export function createSecurityPolicy({
  development = process.env.NODE_ENV === "development",
  apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1",
  supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || process.env.SUPABASE_URL,
}: SecurityPolicyOptions = {}) {
  const nonce = btoa(String.fromCharCode(...crypto.getRandomValues(new Uint8Array(16))));
  const connections = new Set(["'self'", configuredOrigin(apiBaseUrl)]);
  if (supabaseUrl) connections.add(configuredOrigin(supabaseUrl));
  if (development) {
    connections.add("ws://localhost:3000");
    connections.add("ws://127.0.0.1:3000");
  }

  const contentSecurityPolicy = [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${development ? " 'unsafe-eval'" : ""}`,
    // Next's development overlay/HMR injects styles without nonces. Production
    // accepts only bundled same-origin CSS and framework styles with this nonce.
    `style-src 'self' ${development ? "'unsafe-inline'" : `'nonce-${nonce}'`}`,
    "style-src-attr 'none'",
    "img-src 'self' data: blob:",
    "font-src 'self'",
    `connect-src ${[...connections].join(" ")}`,
    "object-src 'none'",
    "base-uri 'none'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join("; ");

  return { nonce, contentSecurityPolicy };
}
