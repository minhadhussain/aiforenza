"use client";

import { useEffect, useRef, useTransition } from "react";
import { useRouter } from "next/navigation";

export function OverviewRefresh() {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const last = useRef(0);
  useEffect(() => {
    const refresh = () => {
      if (pending || document.visibilityState !== "visible" || Date.now() - last.current < 15000) return;
      last.current = Date.now();
      startTransition(() => router.refresh());
    };
    const interval = window.setInterval(refresh, 15000);
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", refresh);
    return () => { window.clearInterval(interval); window.removeEventListener("focus", refresh); document.removeEventListener("visibilitychange", refresh); };
  }, [router, pending]);
  return <button disabled={pending} className="mt-3 border border-white/20 px-3 py-2 text-sm disabled:opacity-50" onClick={() => {
    last.current = Date.now(); startTransition(() => router.refresh());
  }}>{pending ? "Refreshing dashboard…" : "Refresh dashboard"}</button>;
}
