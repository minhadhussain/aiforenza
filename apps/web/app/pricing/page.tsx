import Link from "next/link";

import { PublicShell } from "@/components/home/public-shell";
import { SectionHero } from "@/components/home/section-hero";

const topups = ["$10", "$25", "$50", "$100", "$500", "$1,000"];

export default function PricingPage() {
  return (
    <PublicShell>
      <SectionHero
        eyebrow="Pricing"
        title="Simple usage-based pricing."
        copy="$5 free credit to get started. Then pay only for what you use through prepaid balance top-ups."
      />

      <section className="mt-14 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {topups.map((amount) => (
          <article key={amount} className="rounded-[1.75rem] border border-white/8 bg-white/[0.03] px-6 py-8 text-center transition hover:border-white/16 hover:bg-white/[0.05]">
            <div className="font-[family-name:var(--font-heading)] text-4xl text-white">{amount}</div>
            <div className="mt-3 text-xs uppercase tracking-[0.24em] text-[var(--muted)]">Prepaid balance</div>
            <p className="mt-5 text-sm leading-7 text-[var(--muted)]">Add credits to your wallet, authenticate with one API key, and consume balance as requests are charged.</p>
          </article>
        ))}
      </section>

      <section className="mt-16 grid gap-4 md:grid-cols-3">
        {[
          ["Start free", "Every new developer account begins with free API credit so you can validate the integration path quickly."],
          ["Pay only for usage", "Charges are based on model usage records and deducted from a prepaid wallet balance."],
          ["No subscriptions", "No monthly plan matrix, no seat tiers, and no billing complexity beyond your wallet balance."],
        ].map(([title, copy]) => (
          <article key={title} className="rounded-[1.75rem] border border-white/8 bg-white/[0.025] p-6 transition hover:border-white/14 hover:bg-white/[0.035]">
            <h2 className="font-[family-name:var(--font-heading)] text-xl text-white">{title}</h2>
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{copy}</p>
          </article>
        ))}
      </section>

      <section className="mt-16 flex flex-col items-center rounded-[2rem] border border-white/8 px-6 py-16 text-center shadow-[var(--shadow)] sm:px-10">
        <h2 className="font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">Ready to make your first request?</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-[var(--muted)]">Create an account, receive free credit, generate an API key, and top up only when usage becomes real.</p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
            Start Free
          </Link>
          <Link className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.02] px-6 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.05]" href="/docs">
            Quickstart Docs
          </Link>
        </div>
      </section>
    </PublicShell>
  );
}
