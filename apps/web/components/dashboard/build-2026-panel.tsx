"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import Image from "next/image";
import Link from "next/link";
import type { HackathonStatus } from "@/lib/hackathon";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import { formatUsdFromCents } from "@/lib/dashboard";
import styles from "./build-2026.module.css";

const eventUrl = "https://hackyard.org/build2026";

function Arrow() {
  return <span aria-hidden="true">↗</span>;
}

export function Build2026Panel({ initial, userId }: { initial: HackathonStatus; userId: string }) {
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
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : body.detail?.message || body.error?.message || "Unable to load BUILD 2026 credits. Check status before retrying.");
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
  const creditAmount = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0, maximumFractionDigits: 2 }).format((data.campaign?.grant_amount_cents ?? 10000) / 100);

  return <div className={styles.event} data-testid="build-2026-page">
    <header className={styles.masthead}>
      <a href={eventUrl} target="_blank" rel="noopener noreferrer" className={styles.eventBrand}>
        <Image src="/build2026/hackyard-icon.png" width={36} height={36} alt="" />
        <span><strong>Hackyard</strong><small>presents BUILD 2026</small></span>
      </a>
      <span className={styles.collaboration}>× <strong>AI Forenza</strong></span>
      <a href={eventUrl} target="_blank" rel="noopener noreferrer" className={styles.eventLink}>Official event <Arrow /></a>
    </header>

    <section className={styles.hero} aria-labelledby="build-title">
      <div className={styles.heroCopy}>
        <p className={styles.eyebrow}>Don’t build alone.</p>
        <h1 id="build-title" aria-label="BUILD 2026" className={styles.heroTitle}><span>BUILD</span><span className={styles.outline}>2026</span></h1>
        <p className={styles.heroSubtitle}>Your next idea.<br />Powered by AI Forenza.</p>
        <p className={styles.heroDescription}>AI credits for selected BUILD 2026 projects. Bring the idea. We’ll bring the models. Make something real.</p>
        <div className={styles.actions}>
          <a href="#claim-credits" className={styles.primaryButton}>Get your AI credits <span className={styles.arrowBox}><Arrow /></span></a>
          <a href="#how-it-works" className={styles.textLink}>How it works <Arrow /></a>
        </div>
        <p className={styles.heroNote}>One project. One allocation. More room to build.</p>
      </div>
      <div className={styles.artwork} role="img" aria-label={`${creditAmount} in AI Forenza credits per selected project`}>
        <Image src="/build2026/builder.png" width={1012} height={1246} alt="" priority sizes="(max-width: 700px) 80vw, 40vw" className={styles.builder} />
        <div className={styles.creditSeal} aria-hidden="true">
          <span>AI FORENZA</span><strong>{creditAmount}</strong><span>AI CREDITS</span><small>PER SELECTED PROJECT</small>
        </div>
      </div>
    </section>

    <dl className={styles.eventFacts}>
      <div><dt>The physical build</dt><dd>24–25 Oct 2026</dd></div>
      <div><dt>The place</dt><dd>IIT Guwahati</dd></div>
      <div><dt>The challenge</dt><dd>24 hours. Make it work.</dd></div>
      <div><dt>Your people</dt><dd>Solo or teams of 2–4</dd></div>
    </dl>

    <section id="claim-credits" className={styles.claimSection} aria-labelledby="claim-title">
      <div className={styles.creditOffer}>
        <p className={styles.eyebrow}>For the builders / AI credit allocation</p>
        <h2 id="claim-title">Less friction.<br />More building.</h2>
        <p className={styles.offerValue}>{creditAmount}<span>in AI Forenza credits</span></p>
        <p>A solo build gets one allocation. A team shares one allocation for its project. Use it to prototype, experiment, and bring your demo to life.</p>
        <div className={styles.offerFooter}><span>BUILD 2026</span><span>BUILD SOMETHING REAL <Arrow /></span></div>
      </div>
      <div className={styles.claimPanel}>
        {error && <p role="alert" className={styles.error}>{error}</p>}
        {secret ? <div className={styles.keyReveal}>
          <p className={styles.eyebrow}>Allocation claimed / Team {revealedTeam}</p>
          <h3>You’re ready<br />to build.</h3>
          <p>Copy your project’s shared API key now. This is the only time the full key is shown.</p>
          <code data-testid="hackathon-secret" className={styles.secret}>{secret}</code>
          <div className={styles.actions}>
            <button type="button" className={styles.primaryButton} onClick={async () => { try { await navigator.clipboard.writeText(secret); setCopied(true); } catch { setError("Clipboard unavailable; copy the displayed key manually."); } }}>{copied ? "Copied" : "Copy API Key"}<Arrow /></button>
            <button type="button" className={styles.textLink} onClick={() => setSecret(null)}>I saved it — hide key</button>
          </div>
          <a href="/dashboard/docs/opencode#quick-setup" target="_blank" rel="noopener noreferrer" className={styles.setupLink}>Set up OpenCode <Arrow /><small>Opens in a new tab so your key stays here.</small></a>
          <p className={styles.finePrint}>Share this key privately with your project teammates. Everyone with it uses the same promotional balance.</p>
        </div> : <>
          <p className={styles.claimStatus}><span className={data.campaign ? styles.liveDot : styles.waitingDot} />{data.campaign ? "Credit claims are open" : "Waiting for credit claims to open"}</p>
          <h3>Your build<br />starts here.</h3>
          <p>Enter the credit-claim Team ID provided by the BUILD 2026 organizers.</p>
          {data.campaign ? <form onSubmit={claim} className={styles.claimForm}>
            <label htmlFor="build-team-id">Team ID</label>
            <input id="build-team-id" aria-describedby="build-team-help" required minLength={3} maxLength={64} value={teamId} onChange={e => setTeamId(e.target.value)} autoComplete="off" spellCheck={false} placeholder="Your organizer-issued Team ID" />
            <button type="submit" disabled={busy || !validSession.current} className={styles.primaryButton}>{busy ? "Claiming…" : `Claim ${creditAmount} Credit`}<span className={styles.arrowBox}><Arrow /></span></button>
            <p id="build-team-help" className={styles.finePrint}>One claim per project. If a teammate has already claimed, ask them for the shared API key.</p>
            <p className={styles.campaignName}>Credit campaign: {data.campaign.name}</p>
          </form> : <div className={styles.waitingNotice}>
            <p>The organizers will share credit-claim instructions when your allocation is ready. You can prepare your OpenCode setup in the meantime.</p>
            <Link href="/dashboard/docs/opencode" className={styles.textLink}>Get ready with OpenCode <Arrow /></Link>
          </div>}
          <a href="mailto:hello@hackyard.org" className={styles.helpLink}>Need your credit-claim Team ID? Ask the organizers <Arrow /></a>
        </>}
      </div>
    </section>

    {data.grants.length > 0 && <section className={styles.section} aria-labelledby="project-credits-title">
      <div className={styles.sectionHeading}><div><p className={styles.eyebrow}>Your allocation</p><h2 id="project-credits-title">Keep the build going.</h2></div><button type="button" disabled={busy} onClick={() => void refresh()} className={styles.secondaryButton}>Refresh promotional balance <span aria-hidden="true">↻</span></button></div>
      <div className={styles.grantGrid}>{data.grants.map(grant => <article key={`${grant.campaign_name}/${grant.team_id}`} className={styles.grant}>
        <div className={styles.grantHeader}><h3>Team: {grant.team_id}</h3><span>{grant.key_revoked ? "KEY REVOKED" : grant.status}</span></div>
        <p className={styles.campaignName}>{grant.campaign_name}</p>
        <p className={styles.eyebrow}>Available promotional balance</p>
        <p data-testid="promo-available" className={styles.balance}>{formatUsdFromCents(grant.available_balance_cents)}</p>
        <dl className={styles.balanceDetails}><div><dt>Total</dt><dd>{formatUsdFromCents(grant.promo_balance_cents)}</dd></div><div><dt>Reserved</dt><dd>{formatUsdFromCents(grant.reserved_cents)}</dd></div><div><dt>Billing</dt><dd>Promotional</dd></div></dl>
        <p className={styles.finePrint}>API Key: sk_af_**************** · Shared project credit, billed at reference price. Your personal wallet stays separate.</p>
        <div className={styles.actions}><Link href="/dashboard/usage" className={styles.textLink}>View usage <Arrow /></Link><Link href="/dashboard/api-keys" className={styles.textLink}>Manage key <Arrow /></Link></div>
      </article>)}</div>
    </section>}

    <section id="how-it-works" className={styles.section} aria-labelledby="steps-title">
      <div className={styles.sectionHeading}><div><p className={styles.eyebrow}>From idea to your first request</p><h2 id="steps-title">Claim. Connect. Build.</h2></div><p>Three steps between<br />your idea and your first API call.</p></div>
      <ol className={styles.steps}>
        <li><span className={styles.stepNumber}>01</span><h3>Claim your credits.</h3><p>Use your organizer-issued Team ID. Save the shared API key and pass it privately to your teammates.</p><a href="#claim-credits" className={styles.textLink}>Claim allocation <Arrow /></a></li>
        <li><span className={styles.stepNumber}>02</span><h3>Connect your tools.</h3><p>Paste one setup command to create your OpenCode configuration. Connect your key and choose an AI Forenza model.</p><a href="/dashboard/docs/opencode#quick-setup" target="_blank" rel="noopener noreferrer" className={styles.textLink}>Set up OpenCode <Arrow /><span className="sr-only"> (opens in a new tab)</span></a></li>
        <li><span className={styles.stepNumber}>03</span><h3>Make it real.</h3><p>Build an agent, a useful tool, or something completely your own. Test your idea, watch your usage, and ship a working demo.</p><Link href="/dashboard/docs" className={styles.textLink}>Explore the API docs <Arrow /></Link></li>
      </ol>
    </section>

    <div className={styles.buildStrip} aria-hidden="true"><span>IDEA</span><span>↗</span><span>BUILD</span><span>↗</span><span>TEST</span><span>↗</span><span>SHOW</span><span>✳</span></div>

    <section className={styles.section} aria-labelledby="ideas-title">
      <div className={styles.sectionHeading}><div><p className={styles.eyebrow}>Your idea. Your build.</p><h2 id="ideas-title">What will<br /><span className={styles.outline}>you build?</span></h2></div><p>No assigned problem. Start with something worth making and use AI Forenza to bring it to life.</p></div>
      <div className={styles.ideas}>
        <article className={styles.ideaCard}><Image src="/build2026/idea-agent.svg" width={210} height={180} alt="" /><div><h3>Make AI do more.</h3><p>Give your project the ability to reason, create, and act. Build an agent that does useful work.</p><Link href="/dashboard/models" className={styles.textLink}>Explore models <Arrow /></Link></div></article>
        <article className={`${styles.ideaCard} ${styles.blueIdea}`}><Image src="/build2026/idea-tool.svg" width={210} height={180} alt="" /><div><h3>Reinvent the everyday.</h3><p>Start with a real problem. Make a tool that changes how people work, learn, or collaborate.</p><Link href="/dashboard/docs/quickstart" className={styles.textLink}>Make your first request <Arrow /></Link></div></article>
      </div>
    </section>

    <section className={styles.eventDetails} aria-labelledby="event-details-title">
      <div><p className={styles.eyebrow}>Hackyard / The physical build</p><h2 id="event-details-title">24 hours.<br />Something real.</h2></div>
      <div><p>Join the selected builders at <strong>IIT Guwahati, 24–25 October 2026</strong>. Build solo or with a team of 2–4. Bring a laptop, your curiosity, and something worth making.</p><p>Applications closed on 10 October. Selection, the participant package, and arrival details are managed by Hackyard.</p><div className={styles.actions}><a href={`${eventUrl}/guide`} target="_blank" rel="noopener noreferrer" className={styles.textLink}>Read the builder guide <Arrow /></a><a href={`${eventUrl}/result`} target="_blank" rel="noopener noreferrer" className={styles.textLink}>Selected projects <Arrow /></a></div></div>
    </section>

    <section className={`${styles.section} ${styles.faq}`} aria-labelledby="questions-title">
      <div><p className={styles.eyebrow}>A few things to know</p><h2 id="questions-title">Good<br />questions.</h2><a href="mailto:hello@hackyard.org" className={styles.textLink}>Ask the organizing team <Arrow /></a></div>
      <div>
        {[
          ["Who gets the credits?", `Selected BUILD 2026 projects receive one ${creditAmount} AI Forenza credit allocation. A solo builder receives it for their project; a team of 2–4 shares one allocation. It is per project, not per person.`],
          ["Which Team ID should I enter?", "Use the credit-claim Team ID shared by the BUILD 2026 organizers. A Hackyard application or team-invite code works here only if the organizers have enabled it for AI Forenza credits. If you are unsure, contact hello@hackyard.org."],
          ["A teammate already claimed. What should I do?", "Ask that teammate for the shared API key and use it to connect your tools. Each project claims once, and every teammate’s requests use the same promotional balance."],
          ["Can I claim again after refreshing or changing accounts?", "No. Your project's claim is recorded in the database. Refreshing, clearing browser data, using another device or account, or changing your IP with a VPN cannot reset it. Simultaneous requests can create only one allocation. Spending the credits or revoking the key does not make the Team ID claimable again."],
          ["How are the credits used?", "Your shared key spends only its promotional allocation. API usage is charged at reference price, without the personal-wallet discount. Reservations reduce available credit while requests are running. Usage stops when there is not enough available credit; your personal wallet is not charged as a fallback."],
          ["Can I see the full API key again?", "The full key appears only when the claim succeeds. Save it before leaving or reloading this page. If it is lost, contact the organizers; claiming the same Team ID again will not reveal or recreate it."],
          ["Are these cash prizes or other partner credits?", "These are AI Forenza API credits for your project. Hackyard manages event prizes and other partner offers separately. Visit the official BUILD 2026 site for their eligibility and redemption details."],
        ].map(([question, answer]) => <details key={question}><summary>{question}<span aria-hidden="true">+</span></summary><p>{answer}</p></details>)}
      </div>
    </section>

    <footer className={styles.footer}><div><span className={styles.eyebrow}>Hackyard BUILD 2026 × AI Forenza</span><p>Don’t just talk. Make it real.</p></div><a href={eventUrl} target="_blank" rel="noopener noreferrer" className={styles.textLink}>Visit BUILD 2026 <Arrow /></a>{data.grants.length === 0 && <button type="button" disabled={busy} onClick={() => void refresh()} className={styles.textLink}>Refresh promotional balance <span aria-hidden="true">↻</span></button>}</footer>
  </div>;
}
