import Image from "next/image";
import Link from "next/link";

import { build2026Fonts } from "@/components/build-2026/fonts";
import styles from "./build-2026-promotion.module.css";

export function Build2026Promotion() {
  return (
    <section id="build-2026" aria-labelledby="build-2026-invitation" className={`${build2026Fonts} ${styles.promotion}`}>
      <div className={styles.brandBar}>
        <a href="https://hackyard.org/build2026" target="_blank" rel="noopener noreferrer" className={styles.brand}>
          <Image src="/build2026/hackyard-icon.png" width={34} height={34} alt="" />
          <span>Hackyard<small>presents BUILD 2026</small></span>
        </a>
        <span className={styles.collaboration}>× <strong>AI Forenza</strong></span>
        <span className={styles.edition}>Ideas → working software</span>
      </div>

      <div className={styles.content}>
        <div className={styles.copy}>
          <p className={styles.eyebrow}>Don’t build alone.</p>
          <h2 id="build-2026-invitation">Join the build.<br /><span>BUILD 2026.</span></h2>
          <p className={styles.description}>We’re backing the builders at Hackyard BUILD 2026 with <strong>$100 in AI Forenza credits per selected project.</strong> Bring your idea. Build an agent, make a useful tool, or try something entirely your own.</p>
          <div className={styles.actions}>
            <Link href="/dashboard/build-2026" className={styles.primaryLink}>Claim BUILD 2026 credits <span aria-hidden="true">↗</span></Link>
            <a href="https://hackyard.org/build2026" target="_blank" rel="noopener noreferrer" className={styles.textLink}>Explore the event <span aria-hidden="true">↗</span></a>
          </div>
          <p className={styles.accountLink}>New to AI Forenza? <Link href="/signup?next=%2Fdashboard%2Fbuild-2026">Create an account to get started.</Link></p>
          <p className={styles.eligibility}>One allocation per project, shared by teammates. Claim with your single-use, organizer-issued Team ID. Applications closed on 10 October; selection is managed by Hackyard.</p>
        </div>
        <div className={styles.artwork} role="img" aria-label="$100 in AI Forenza credits per selected BUILD 2026 project">
          <Image src="/build2026/builder.png" width={1012} height={1246} alt="" sizes="(max-width: 700px) 85vw, 40vw" className={styles.builder} />
          <div className={styles.seal} aria-hidden="true"><span>AI FORENZA</span><strong>$100</strong><span>AI CREDITS</span><small>PER SELECTED PROJECT</small></div>
        </div>
      </div>

      <dl className={styles.details}>
        <div><dt>When</dt><dd>24–25 October 2026</dd></div>
        <div><dt>Where</dt><dd>IIT Guwahati</dd></div>
        <div><dt>Who</dt><dd>Solo or teams of 2–4</dd></div>
        <div><dt>The mission</dt><dd>24 hours. Make it real.</dd></div>
      </dl>
    </section>
  );
}
