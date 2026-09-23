"use client";

import { useRef, useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { ensureAccountReady, safeDashboardPath } from "@/lib/auth";

type LoginFormProps = {
  nextPath: string;
  initialError?: string;
};

export function LoginForm({ nextPath, initialError }: LoginFormProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(initialError ?? null);
  const [loading, setLoading] = useState(false);
  const submitting = useRef(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (submitting.current) return;
    // Read the submitted inputs, including password-manager/autofill values.
    const form = new FormData(event.currentTarget);
    submitting.current = true;
    setLoading(true);
    setError(null);

    let navigating = false;
    try {
      const supabase = createSupabaseBrowserClient();
      const { data, error: signInError } = await supabase.auth.signInWithPassword({
        email: String(form.get("email") ?? "").trim(),
        password: String(form.get("password") ?? ""),
      });

      if (signInError) {
        setError(signInError.name === "AuthRetryableFetchError"
          ? "Unable to reach the sign-in service. Please try again."
          : signInError.message);
        return;
      }
      if (!data.session) {
        setError("Sign-in did not create a session. Please try again.");
        return;
      }

      await ensureAccountReady(data.session.access_token);
      // Begin one fresh server render with the persisted auth cookies. This also
      // avoids racing router.push with router.refresh against stale guest data.
      window.location.assign(safeDashboardPath(nextPath));
      navigating = true;
    } catch {
      setError("Unable to sign in right now. Please try again.");
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
        <p className="text-sm uppercase tracking-[0.25em] text-[var(--muted)]">Welcome back</p>
        <h2 className="mt-3 font-[family-name:var(--font-heading)] text-3xl">Log in to the dashboard</h2>
      </div>

      <label className="block space-y-2 text-sm font-medium text-[var(--text)]">
        <span>Email</span>
        <input
          className="w-full rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-base outline-none ring-0 transition focus:border-[var(--accent)]"
          type="email"
          name="email"
          autoComplete="username"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@company.com"
          required
        />
      </label>

      <label className="block space-y-2 text-sm font-medium text-[var(--text)]">
        <span>Password</span>
        <input
          className="w-full rounded-2xl border border-[var(--border)] bg-[var(--surface-strong)] px-4 py-3 text-base outline-none ring-0 transition focus:border-[var(--accent)]"
          type="password"
          name="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="Your password"
          required
        />
      </label>

      {error ? <p role="alert" className="rounded-2xl bg-[#f7d9cb] px-4 py-3 text-sm text-[#7f2d12]">{error}</p> : null}

      <button
        className="inline-flex w-full items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-base font-semibold text-black transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={loading}
      >
        {loading ? "Signing in..." : "Log in"}
      </button>

    </form>
  );
}
