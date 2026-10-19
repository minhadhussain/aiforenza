"use client";

import { useEffect, useRef, useState } from "react";

import { ensureAccountReady, isTemporaryAuthError, safeDashboardPath } from "@/lib/auth";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const retryMessage = "We couldn’t finish loading your account. Please try again; you don’t need to create another account.";

export function AccountSetup({ nextPath, retryRequired = false }: { nextPath: string; retryRequired?: boolean }) {
  const [attempt, setAttempt] = useState(0);
  const [error, setError] = useState<string | null>(retryRequired ? retryMessage : null);
  const [progress, setProgress] = useState("Checking your session…");
  // Strict Mode may re-run effects. Share the in-flight setup within this mount.
  const pending = useRef<Promise<"ready" | "sign-in" | "verify-email"> | null>(null);

  useEffect(() => {
    if (retryRequired && attempt === 0) return;
    let active = true;
    setError(null);
    setProgress("Setting up your account…");
    if (!pending.current) {
      pending.current = (async () => {
        const supabase = createSupabaseBrowserClient();
        const { data: { user }, error: userError } = await supabase.auth.getUser();
        if (userError) {
          if (isTemporaryAuthError(userError)) throw userError;
          return "sign-in" as const;
        }
        if (!user) return "sign-in" as const;
        if (!user.email_confirmed_at) return "verify-email" as const;
        const { data: { session }, error: sessionError } = await supabase.auth.getSession();
        if (sessionError) throw sessionError;
        if (!session?.access_token) return "sign-in" as const;
        await ensureAccountReady(session.access_token);
        return "ready" as const;
      })();
    }
    void pending.current.then((result) => {
      if (!active) return;
      if (result === "verify-email") {
        pending.current = null;
        setError("Verify your email using the confirmation link before claiming credits or creating API keys. Then retry account setup.");
        return;
      }
      if (result === "sign-in") {
        window.location.replace(`/login?${new URLSearchParams({ next: safeDashboardPath(nextPath) })}`);
        return;
      }
      setProgress("Opening your dashboard…");
      window.location.replace(safeDashboardPath(nextPath));
    }).catch(() => {
      if (!active) return;
      pending.current = null;
      setError(retryMessage);
    });
    return () => { active = false; };
  }, [attempt, nextPath, retryRequired]);

  return (
    <div className="space-y-5">
      <h2 className="font-[family-name:var(--font-heading)] text-2xl">Finishing sign-in</h2>
      {error ? <>
        <p role="alert" className="rounded-2xl bg-[#f7d9cb] px-4 py-3 text-sm text-[#7f2d12]">{error}</p>
        <button type="button" onClick={() => setAttempt(value => value + 1)} className="w-full rounded-full bg-[var(--accent)] px-6 py-3 font-semibold text-black">Retry account setup</button>
      </> : <p role="status" aria-live="polite" className="text-sm text-[var(--muted)]">{progress}</p>}
    </div>
  );
}
