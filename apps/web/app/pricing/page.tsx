"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PublicShell } from "@/components/home/public-shell";
import { SectionHero } from "@/components/home/section-hero";
import { fetchPublicModels } from "@/lib/public-models";
import { formatModelRate } from "@/lib/dashboard";
import type { DashboardModel } from "@/lib/dashboard";

export default function PricingPage() {
  const [models, setModels] = useState<DashboardModel[]>([]);
  const [message, setMessage] = useState("Loading configured pricing...");

  useEffect(() => {
    let active = true;
    fetchPublicModels()
      .then((data) => {
        if (active) { setModels(data); setMessage("No enabled models are available."); }
      })
      .catch(() => {
        if (active) { setModels([]); setMessage("Pricing is temporarily unavailable. Please try again later."); }
      });

    return () => {
      active = false;
    };
  }, []);

  const pricedPreview = useMemo(() => models.slice(0, 4), [models]);

  return (
    <PublicShell>
      <SectionHero
        eyebrow="PRICING"
        title="Simple usage-based pricing."
        copy="Pay for what you use. No monthly plans."
      />

      <section className="mt-14 rounded-[2rem] border border-white/8 bg-white/[0.025] px-6 py-10 shadow-[var(--shadow)] sm:px-8">
        <div className="grid gap-6 lg:grid-cols-[0.7fr_1.6fr_0.7fr] lg:items-center">
          {[
            ["ADD BALANCE", "Choose an amount."],
            ["USE ANY MODEL", "One API. Multiple models."],
            ["PAY FOR USAGE", "Only what you consume."],
          ].map(([title, copy], index) => (
            <div key={title} className="text-center">
              <div className="text-sm uppercase tracking-[0.24em] text-white/75">{title}</div>
              <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{copy}</p>
              {index < 2 ? <div className="mx-auto mt-6 hidden h-px w-16 bg-gradient-to-r from-transparent via-white/14 to-transparent lg:block" /> : null}
            </div>
          ))}
        </div>
      </section>

      <section className="mt-12 grid gap-4 md:grid-cols-3">
        {[
          ["NO SUBSCRIPTIONS", "Use credit when you need it."],
          ["ONE API", "Access multiple models."],
          ["TRANSPARENT", "See what you spend."],
        ].map(([title, copy]) => (
          <article key={title} className="rounded-[1.75rem] border border-white/8 bg-white/[0.025] p-6 transition hover:border-white/14 hover:bg-white/[0.035]">
            <h2 className="font-[family-name:var(--font-heading)] text-xl text-white">{title}</h2>
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{copy}</p>
          </article>
        ))}
      </section>

      <section className="mt-16 rounded-[2rem] border border-white/8 bg-white/[0.025] px-6 py-12 shadow-[var(--shadow)] sm:px-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.22em] text-[var(--muted)]">Model pricing</p>
            <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Configured customer-facing pricing is model-driven. AI Forenza applies the current discount structure on top of the model reference price.</p>
          </div>
          <Link className="text-sm text-white/72 transition hover:text-white" href="/models">
            View all models →
          </Link>
        </div>

        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {!pricedPreview.length && <p role="status" className="text-sm text-[var(--muted)]">{message}</p>}
          {pricedPreview.map((model) => (
            <div key={model.id} className="rounded-[1.25rem] border border-white/8 bg-white/[0.03] px-4 py-4">
              <div className="text-sm font-semibold text-white">{model.display_name}</div>
              <div className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">Discount</div>
                  <div className="mt-2 text-white">{model.discount_percent}%</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">Input / 1M</div>
                  <div className="mt-2 text-white">{formatModelRate(model.customer_input_price_per_million)}</div>
                </div>
                <div>
                  <div className="text-[11px] uppercase tracking-[0.16em] text-[var(--muted)]">Output / 1M</div>
                  <div className="mt-2 text-white">{formatModelRate(model.customer_output_price_per_million)}</div>
                </div>
              </div>
              <div className="mt-4 text-xs text-[var(--muted)]">Reference pricing remains server-configured. Customer-facing pricing is calculated with the configured discount before wallet deduction.</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-16 rounded-[2rem] border border-white/8 bg-white/[0.025] px-6 py-12 shadow-[var(--shadow)] sm:px-8">
        <div className="max-w-2xl">
          <p className="text-sm uppercase tracking-[0.22em] text-[var(--muted)]">START FREE</p>
          <p className="mt-4 text-base leading-8 text-white">New accounts get $5 in API credit.</p>
          <div className="mt-6">
            <Link className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
              Create your account →
            </Link>
          </div>
        </div>
      </section>

      <section className="mt-16 flex flex-col items-center rounded-[2rem] border border-white/8 px-6 py-16 text-center shadow-[var(--shadow)] sm:px-10">
        <h2 className="font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">Build without a pricing maze.</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-[var(--muted)]">Start free. Choose your model. Pay as you go.</p>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
            Start Free →
          </Link>
          <Link className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.02] px-6 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.05]" href="/docs">
            Read the Docs
          </Link>
        </div>
      </section>
    </PublicShell>
  );
}
