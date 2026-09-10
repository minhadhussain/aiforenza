"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { ActivityPage } from "@/lib/activity";
import { formatUsdFromCents } from "@/lib/dashboard";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

const statusLabels = { billed: "Completed · billed", unsettled: "In progress / unsettled", rejected: "Rejected · no inference", released: "Released · not billed" };
const control = "border border-white/20 bg-[#111318] px-3 py-2 text-sm text-white disabled:opacity-50";

export function UsageActivity({ initial }: { initial: ActivityPage }) {
  const router = useRouter();
  const [data, setData] = useState<ActivityPage | null>(initial);
  const [model, setModel] = useState("");
  const [key, setKey] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updated, setUpdated] = useState(initial.as_of);
  const active = useRef<AbortController | null>(null);
  const sequence = useRef(0);
  const anchor = useRef(initial.as_of);
  const lastStart = useRef(0);
  const failures = useRef(0);
  const first = useRef(true);

  const load = useCallback(async (fresh = false, background = false) => {
    if (background && (document.visibilityState !== "visible" || active.current || Date.now() - lastStart.current < 3000)) return;
    active.current?.abort();
    const controller = new AbortController();
    active.current = controller;
    const id = ++sequence.current;
    lastStart.current = Date.now();
    setLoading(true);
    const timeout = window.setTimeout(() => controller.abort(), 30000);
    try {
      const supabase = createSupabaseBrowserClient();
      const { data: { session } } = await supabase.auth.getSession();
      if (id !== sequence.current || controller.signal.aborted) return;
      if (!session || session.user.id !== initial.account.id) {
        setData(null);
        router.refresh();
        throw new Error("Account changed or session expired. Sign in again to view usage.");
      }
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
      if (model) params.set("model", model);
      if (key) params.set("api_key_id", key);
      if (status) params.set("activity_status", status);
      if (!fresh && anchor.current) params.set("as_of", anchor.current);
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1"}/dashboard/activity?${params}`, {
        headers: { Authorization: `Bearer ${session.access_token}` }, cache: "no-store", signal: controller.signal,
      });
      if (id !== sequence.current || controller.signal.aborted) return;
      if (response.status === 401) { setData(null); throw new Error("Session expired. Please sign in again."); }
      if (!response.ok) throw new Error("Unable to refresh activity. Your last successful results are shown; retry shortly.");
      const payload = await response.json() as ActivityPage;
      if (id !== sequence.current || controller.signal.aborted) return;
      if (payload.account.id !== initial.account.id) { setData(null); throw new Error("Account changed. Reload this page."); }
      if (id !== sequence.current || controller.signal.aborted) return;
      anchor.current = payload.as_of;
      failures.current = 0;
      setData(payload);
      setUpdated(new Date().toISOString());
      setError(null);
    } catch (caught) {
      if (id === sequence.current) {
        failures.current++;
        setError(controller.signal.aborted ? "Activity refresh timed out. Try Refresh usage." : caught instanceof Error ? caught.message : "Activity refresh failed.");
      }
    } finally {
      window.clearTimeout(timeout);
      if (id === sequence.current) { active.current = null; setLoading(false); }
    }
  }, [page, pageSize, model, key, status, initial.account.id, router]);

  useEffect(() => {
    if (first.current) first.current = false;
    else void load(page === 1);
    const tick = () => {
      const interval = Math.min(120000, 15000 * 2 ** Math.min(failures.current, 3));
      if (Date.now() - lastStart.current >= interval) void load(page === 1, true);
    };
    const onFocus = () => { void load(page === 1, true); };
    const timer = window.setInterval(tick, 1000);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onFocus);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onFocus);
      sequence.current++;
      active.current?.abort();
      active.current = null;
    };
  }, [load, page]);

  useEffect(() => {
    const { data: { subscription } } = createSupabaseBrowserClient().auth.onAuthStateChange((_event, session) => {
      if (!session || session.user.id !== initial.account.id) {
        sequence.current++;
        active.current?.abort();
        active.current = null;
        setData(null);
        setLoading(false);
        setError("Account changed or signed out. Reload to view the current account.");
        router.refresh();
      }
    });
    return () => subscription.unsubscribe();
  }, [initial.account.id, router]);

  const reset = (setter: (value: string) => void, value: string) => { anchor.current = ""; setPage(1); setter(value); };
  const refresh = () => { anchor.current = ""; if (page !== 1) setPage(1); else void load(true); };
  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / pageSize));

  return <div className="space-y-6">
    <header>
      <h1 className="font-mono text-lg text-white">USAGE & REQUEST ACTIVITY</h1>
      <p className="mt-3 text-sm">Signed in as <strong>{initial.account.email}</strong></p>
      <p className="break-all font-mono text-xs text-[var(--muted)]">Account ID: {initial.account.id}</p>
      <p className="mt-2 text-sm text-[var(--muted)]">Only this account&apos;s API keys and requests are shown. A key from another account uses that account&apos;s wallet and history.</p>
    </header>
    <div className="flex flex-wrap items-end gap-3">
      <label className="text-sm">Model<select aria-label="Filter model" className={`${control} mt-1 block max-w-60`} value={model} onChange={e => reset(setModel, e.target.value)}>
        <option value="">All models</option>{data?.models.map(m => <option key={m.slug} value={m.slug}>{m.name || m.slug}</option>)}
      </select></label>
      <label className="text-sm">API key<select aria-label="Filter API key" className={`${control} mt-1 block max-w-72`} value={key} onChange={e => reset(setKey, e.target.value)}>
        <option value="">All keys</option>{data?.keys.map(k => <option key={k.id} value={k.id}>{k.name} · {k.id}</option>)}
      </select></label>
      <label className="text-sm">Status<select aria-label="Filter status" className={`${control} mt-1 block`} value={status} onChange={e => reset(setStatus, e.target.value)}>
        <option value="">All statuses</option>{Object.entries(statusLabels).map(([s, label]) => <option key={s} value={s}>{label}</option>)}
      </select></label>
      <label className="text-sm">Rows<select aria-label="Rows per page" className={`${control} mt-1 block`} value={pageSize} onChange={e => { anchor.current = ""; setPage(1); setPageSize(Number(e.target.value)); }}>
        {[10, 25, 50, 100].map(n => <option key={n}>{n}</option>)}
      </select></label>
      <button className={control} disabled={loading} onClick={refresh}>Refresh usage</button>
    </div>
    <p role="status" className="text-xs text-[var(--muted)]">{loading ? "Updating…" : `Updated ${new Date(updated).toISOString().replace("T", " ").slice(0, 19)} UTC`} · Auto-refresh every 15s while visible; backs off on errors. {page > 1 ? "Browsing earlier snapshot. Refresh returns to latest." : ""}</p>
    {error && <p role="alert" className="border border-amber-400/40 p-3 text-sm">{error}</p>}
    <p className="text-sm text-[var(--muted)]">Billed rows contain measured usage. Unsettled rows may be in progress or need reconciliation; held funds are not a charge. Rejected/released rows have no billed usage. Preflight rejection history starts when activity tracking was enabled; older rejected attempts may be absent.</p>
    <section aria-label="Request activity" aria-busy={loading} className="space-y-3">
      {data?.data.map(row => <article data-request-id={row.request_id} key={row.request_id} className="border border-white/15 bg-[#050608] p-4 text-sm">
        <div className="flex flex-wrap justify-between gap-2"><strong>{row.model_name || row.model_slug || "Unknown model"}</strong><span>{statusLabels[row.status]}</span></div>
        <time dateTime={row.created_at} className="text-xs text-[var(--muted)]">{new Date(row.created_at).toISOString().replace("T", " ").slice(0, 19)} UTC</time>
        <p className="mt-2 break-all font-mono text-xs">Request: {row.request_id}</p>
        <p className="mt-1 break-all text-xs">API key: {row.api_key_name || "Deleted/unknown key"} · ID: {row.api_key_id}</p>
        <div className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-[var(--muted)]">
          <span>Input: {row.input_tokens?.toLocaleString() ?? "Not recorded"}</span><span>Output: {row.output_tokens?.toLocaleString() ?? "Not recorded"}</span>
          <span>Cached input: {row.cached_input_tokens?.toLocaleString() ?? "Not recorded"}</span>
          <span>Charged: {row.customer_charge_cents === null ? "Not billed" : formatUsdFromCents(row.customer_charge_cents)}</span>
          {row.status === "billed" && <><span>Reference: {formatUsdFromCents(row.reference_charge_cents)}</span><span>Saved: {formatUsdFromCents(row.customer_savings_cents)}</span></>}
          {row.status === "unsettled" && <span>Held: {formatUsdFromCents(row.reserved_cents)}</span>}
        </div>
        {row.error_code && <p className="mt-2 text-xs">Reason: {row.error_code}{row.http_status ? ` · HTTP ${row.http_status}` : ""}</p>}
      </article>)}
      {data && !data.data.length && <p className="border border-white/10 p-4">No activity matches these filters for this account.</p>}
    </section>
    <nav aria-label="Activity pagination" className="flex items-center gap-4">
      <button className={control} disabled={loading || page === 1} onClick={() => setPage(p => p - 1)}>Previous</button>
      <span>Page {page} of {pages} · {data?.total ?? 0} requests</span>
      <button className={control} disabled={loading || page >= pages} onClick={() => setPage(p => p + 1)}>Next</button>
    </nav>
  </div>;
}
