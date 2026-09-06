"use client";

import Link from "next/link";
import { useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

export function SignupForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    const supabase = createSupabaseBrowserClient();
    const redirectTo = typeof window !== "undefined" ? `${window.location.origin}/auth/callback` : undefined;

    const { error: signUpError, data } = await supabase.auth.signUp({
      email,
      password,
      options: redirectTo ? { emailRedirectTo: redirectTo } : undefined,
    });

    setLoading(false);

    if (signUpError) {
      setError(signUpError.message);
      return;
    }

    if (data.user && data.session) {
      window.location.assign("/dashboard");
      return;
    }

    setSuccess("Account created. Check your email if confirmation is enabled, then continue to the dashboard.");
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
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          placeholder="At least 8 characters"
          minLength={8}
          required
        />
      </label>

      {error ? <p className="rounded-2xl bg-[#f7d9cb] px-4 py-3 text-sm text-[#7f2d12]">{error}</p> : null}
      {success ? <p className="rounded-2xl bg-[#dcefdc] px-4 py-3 text-sm text-[#215e2e]">{success}</p> : null}

      <button
        className="inline-flex w-full items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-base font-semibold text-white transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={loading}
      >
        {loading ? "Creating account..." : "Create account"}
      </button>

      <p className="text-sm text-[var(--muted)]">
        Already have an account? <Link className="font-semibold text-[var(--accent-strong)]" href="/login">Log in</Link>
      </p>
    </form>
  );
}
