"use client";

import { useRef, useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { ensureAccountReady, safeDashboardPath } from "@/lib/auth";

export function SignupForm({ nextPath = "/dashboard", initialError }: { nextPath?: string; initialError?: string }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const submitting = useRef(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    const form = new FormData(event.currentTarget);
    submitting.current = true;
    setLoading(true);
    setError(null);
    setSuccess(null);

    let navigating = false;
    try {
      const supabase = createSupabaseBrowserClient();
      const callback = new URL("/auth/callback", window.location.origin);
      callback.searchParams.set("next", safeDashboardPath(nextPath));
      const { error: signUpError, data } = await supabase.auth.signUp({
        email: String(form.get("email") ?? "").trim(),
        password: String(form.get("password") ?? ""),
        options: { emailRedirectTo: callback.toString() },
      });
      if (signUpError) {
        setError(signUpError.name === "AuthRetryableFetchError" ? "Unable to reach the sign-up service. Please try again." : signUpError.message);
        return;
      }
      if (data.user && data.session) {
        await ensureAccountReady(data.session.access_token);
        window.location.assign(safeDashboardPath(nextPath));
        navigating = true;
        return;
      }
      setSuccess("Check your email for a confirmation link, then sign in to your account.");
    } catch {
      setError("Unable to finish account setup right now. Please try again.");
    } finally {
      if (!navigating) {
        submitting.current = false;
        setLoading(false);
      }
    }
  }

  return (
    <form className="space-y-5" onSubmit={handleSubmit}>
      <div>
        <p className="text-sm uppercase tracking-[0.25em] text-[var(--muted)]">Get started</p>
        <h2 className="mt-3 font-[family-name:var(--font-heading)] text-3xl">Create your account</h2>
      </div>

      <label className="block space-y-2 text-sm font-medium text-[var(--text)]">
        <span>Email</span>
        <input
          className="w-full rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-base outline-none ring-0 transition focus:border-[var(--accent)]"
          type="email"
          name="email"
          autoComplete="username"
          aria-describedby="signup-email-help"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@company.com"
          required
        />
      </label>
      <p id="signup-email-help" className="text-xs text-[var(--muted)]">Use a valid email address, such as you@company.com.</p>

      <label className="block space-y-2 text-sm font-medium text-[var(--text)]">
        <span>Password</span>
        <input
          className="w-full rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-base outline-none ring-0 transition focus:border-[var(--accent)]"
          type="password"
          name="password"
          autoComplete="new-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 8 characters"
          minLength={8}
          required
        />
      </label>

      {error ? <p role="alert" className="rounded-2xl bg-[#f7d9cb] px-4 py-3 text-sm text-[#7f2d12]">{error}</p> : null}
      {success ? <p role="status" className="rounded-2xl bg-[#dcefdc] px-4 py-3 text-sm text-[#215e2e]">{success}</p> : null}

      <button
        className="inline-flex w-full items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-base font-semibold text-black transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={loading}
      >
        {loading ? "Creating account..." : "Create account"}
      </button>

    </form>
  );
}
