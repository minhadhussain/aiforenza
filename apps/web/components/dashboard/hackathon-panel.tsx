"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import type { HackathonStatus } from "@/lib/hackathon";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { formatUsdFromCents } from "@/lib/dashboard";

export function HackathonPanel({ initial, userId }: { initial: HackathonStatus; userId: string }) {
  const [data, setData] = useState(initial);
  const [teamId, setTeamId] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [revealedTeam, setRevealedTeam] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const mounted = useRef(true);
  const inflight = useRef(false);
  const validSession = useRef(true);
  const lastRefresh = useRef(0);
  const request = useCallback(async (path: string, init: RequestInit = {}) => {
    const { data: { session } } = await createSupabaseBrowserClient().auth.getSession();
    if (!session || session.user.id !== userId) throw new Error("Please sign in again to continue.");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/v1"}${path}`, {
      ...init, cache: "no-store", headers: { Authorization: `Bearer ${session.access_token}`, "Content-Type": "application/json" }, signal: AbortSignal.timeout(30000),
    });
    const body = await response.json();
    if (response.status === 401 && mounted.current) {
      validSession.current = false;
      setSecret(null); setData({ campaign: null, grants: [] });
      setError("Session expired. Sign in again to continue.");
      throw new Error("Session expired. Sign in again to continue.");
    }
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : body.detail?.message || body.error?.message || "Unable to load hackathon credits. Check status before retrying.");
    return body;
  }, [userId]);
  const refresh = useCallback(async () => {
    if (inflight.current || !validSession.current) return;
    inflight.current = true; lastRefresh.current = Date.now();
    try { const next = await request("/hackathon/status"); if (mounted.current && validSession.current) { setData(next); setError(null); } }
    catch (e) { if (mounted.current && validSession.current) setError(e instanceof Error ? e.message : "Refresh failed"); }
    finally { inflight.current = false; }
  }, [request]);
  useEffect(() => {
    mounted.current = true;
    const { data: { subscription } } = createSupabaseBrowserClient().auth.onAuthStateChange((_event, session) => {
      if (!session || session.user.id !== userId) {
        validSession.current = false; setSecret(null); setData({ campaign: null, grants: [] }); setError("Account changed or signed out. Reload to continue.");
      }
    });
    const tick = () => { if (document.visibilityState === "visible" && Date.now() - lastRefresh.current > 15000) void refresh(); };
    const timer = window.setInterval(tick, 15000); window.addEventListener("focus", tick);
    return () => { mounted.current = false; subscription.unsubscribe(); window.clearInterval(timer); window.removeEventListener("focus", tick); };
  }, [refresh, userId]);
  async function claim(event: FormEvent) {
    event.preventDefault();
    if (inflight.current || busy || !validSession.current) return;
    inflight.current = true; setBusy(true); setError(null);
    try {
      const body = await request("/hackathon/claim", { method: "POST", body: JSON.stringify({ team_id: teamId }) });
      if (mounted.current && validSession.current) {
        setSecret(body.plaintext_key); setRevealedTeam(body.grant.team_id); setCopied(false);
        setData(previous => ({ ...previous, grants: [body.grant, ...previous.grants] }));
      }
    } catch (e) { if (mounted.current && validSession.current) setError(e instanceof Error ? e.message : "Claim failed. Check grant status before retrying."); }
    finally { inflight.current = false; if (mounted.current) setBusy(false); }
  }
  return <section className="max-w-2xl space-y-5">
    <header><h1 className="font-mono text-lg">HACKATHON CREDITS</h1><p className="mt-2 text-sm text-[var(--muted)]">$100 of reference-priced API usage per organizer-issued Team ID. Promotional requests do not receive the normal paid-wallet discount.</p></header>
    {error && <p role="alert" className="border border-amber-400/30 p-3 text-sm">{error}</p>}
    {secret && <div className="space-y-3 border border-emerald-400/30 p-4">
      <h2 className="text-sm font-semibold">Team: {revealedTeam} · Shared API key</h2>
      <p className="text-sm">Copy this shared API key now. It is shown only once and cannot be retrieved after leaving or reloading this page.</p>
      <code data-testid="hackathon-secret" className="block break-all rounded bg-black p-3 text-sm">{secret}</code>
      <button type="button" className="border border-white/20 px-4 py-2 text-sm" onClick={async () => { try { await navigator.clipboard.writeText(secret); setCopied(true); } catch { setError("Clipboard unavailable; copy the displayed key manually."); } }}>{copied ? "Copied" : "Copy API Key"}</button>
      <button type="button" className="ml-3 text-sm underline" onClick={() => setSecret(null)}>I saved it — hide key</button>
      <p className="text-sm text-[var(--muted)]">Anyone who has this key can use the remaining team credit. Share it privately with your team only. It cannot spend your personal paid wallet.</p>
    </div>}
    {data.campaign ? <form onSubmit={claim} className="space-y-3 border border-white/10 p-4">
      <p className="text-sm">{data.campaign.name}</p>
      <label className="block text-sm">Team ID<input aria-label="Team ID" required minLength={3} maxLength={64} value={teamId} onChange={e => setTeamId(e.target.value)} autoComplete="off" spellCheck={false} className="mt-2 block w-full border border-white/20 bg-black px-3 py-2" placeholder="HACK-042" /></label>
      <button disabled={busy || Boolean(secret)} className="bg-white px-4 py-2 text-sm font-semibold text-black disabled:opacity-50">{busy ? "Claiming…" : "Claim $100 Credit"}</button>
      <p className="text-xs text-[var(--muted)]">Each Team ID can claim once. The first successful claimant receives the shared key; it is not reissued on duplicate claims. Save the key before closing this page.</p>
    </form> : <p className="text-sm text-[var(--muted)]">No hackathon campaign is currently accepting claims.</p>}
    {data.grants.map(grant => <article key={`${grant.campaign_name}/${grant.team_id}`} className="space-y-2 border border-white/10 p-4">
      <h2 className="text-base">Team: {grant.team_id}</h2><p className="text-xs text-[var(--muted)]">{grant.campaign_name} · {grant.status}{grant.key_revoked ? " · KEY REVOKED" : ""}</p>
      <p className="font-mono text-xs text-[var(--muted)]">API Key: sk_af_****************</p>
      <p className="text-sm">Available promotional balance</p><p data-testid="promo-available" className="text-3xl font-semibold">{formatUsdFromCents(grant.available_balance_cents)}</p>
      <p className="text-xs text-[var(--muted)]">Total: {formatUsdFromCents(grant.promo_balance_cents)} · Reserved: {formatUsdFromCents(grant.reserved_cents)} · Billing source: PROMOTIONAL</p>
      <p className="text-xs text-[var(--muted)]">Anyone with the shared key can use this balance. Usage stops when credit runs out. The full key is only shown at claim time; manage revocation in API Keys.</p>
    </article>)}
    <button type="button" disabled={busy} onClick={() => void refresh()} className="border border-white/20 px-4 py-2 text-sm">Refresh promotional balance</button>
  </section>;
}
