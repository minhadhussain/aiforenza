"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

type LoginFormProps = {
  nextPath: string;
};

export function LoginForm({ nextPath }: LoginFormProps) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);

    const supabase = createSupabaseBrowserClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });

    setLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    router.push(/^\/dashboard(?:\/|\?|$)/.test(nextPath) && !nextPath.includes("\\") ? nextPath : "/dashboard");
    router.refresh();
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
          placeholder="Your password"
          required
        />
      </label>

      {error ? <p className="rounded-2xl bg-[#f7d9cb] px-4 py-3 text-sm text-[#7f2d12]">{error}</p> : null}

      <button
        className="inline-flex w-full items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-base font-semibold text-black transition hover:bg-[var(--accent-strong)] disabled:cursor-not-allowed disabled:opacity-60"
        type="submit"
        disabled={loading}
      >
        {loading ? "Signing in..." : "Log in"}
      </button>

      <p className="text-sm text-[var(--muted)]">
        Need an account? <Link className="font-semibold text-[var(--accent-strong)]" href="/signup">Create one</Link>
      </p>
    </form>
  );
}
