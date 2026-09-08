"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { PublicShell } from "@/components/home/public-shell";
import { SectionHero } from "@/components/home/section-hero";
import { publicModelCatalog } from "@/lib/model-catalog";
import { fetchPublicModels } from "@/lib/public-models";
import type { DashboardModel } from "@/lib/dashboard";
import { formatUsdFromCents } from "@/lib/dashboard";

type ModelCategory = "All" | "General" | "Reasoning" | "Coding";

const filters: ModelCategory[] = ["All", "General", "Reasoning", "Coding"];

export default function ModelsPage() {
  const [pricing, setPricing] = useState<Record<string, DashboardModel>>({});
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<ModelCategory>("All");
  const [selectedModel, setSelectedModel] = useState<(typeof publicModelCatalog)[number] | null>(publicModelCatalog[0]);

  useEffect(() => {
    let active = true;

    fetchPublicModels()
      .then((models) => {
        if (!active) return;
        const nextMap = Object.fromEntries(models.map((model) => [model.slug, model]));
        setPricing(nextMap);
      })
      .catch(() => {
        if (!active) return;
        setPricing({});
      });

    return () => {
      active = false;
    };
  }, []);

  const filteredModels = useMemo(() => {
    const normalized = search.trim().toLowerCase();

    return publicModelCatalog.filter((model) => {
      const matchesFilter = activeFilter === "All" || model.category === activeFilter;
      const matchesSearch =
        !normalized ||
        model.name.toLowerCase().includes(normalized) ||
        model.slug.toLowerCase().includes(normalized) ||
        model.category.toLowerCase().includes(normalized);

      return matchesFilter && matchesSearch;
    });
  }, [activeFilter, search]);

  const visibleSelection = selectedModel && filteredModels.some((model) => model.slug === selectedModel.slug)
    ? selectedModel
    : filteredModels[0] ?? null;

  function displayInputPrice(slug: string, fallback: string) {
    const model = pricing[slug];
    if (!model) return fallback;
    return formatUsdFromCents(Math.round(model.customer_input_price_per_million * 100));
  }

  function displayOutputPrice(slug: string, fallback: string) {
    const model = pricing[slug];
    if (!model) return fallback;
    return formatUsdFromCents(Math.round(model.customer_output_price_per_million * 100));
  }

  function displayDiscount(slug: string) {
    const model = pricing[slug];
    if (!model) return null;
    return `${model.discount_percent}% off reference`;
  }

  return (
    <PublicShell>
      <SectionHero
        eyebrow="MODELS"
        title="Choose the model.
Keep the interface."
        copy="Access multiple models through one OpenAI-compatible API."
      />

      <section className="mt-12 grid gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-start">
        <div>
          <div className="smooth-border mb-5 rounded-[1.5rem] bg-white/[0.025] p-4" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <label className="block flex-1">
                <span className="sr-only">Search models</span>
                <input
                  type="text"
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search models..."
                  className="w-full rounded-full border border-white/8 bg-white/[0.03] px-4 py-3 text-sm text-white outline-none transition placeholder:text-[var(--muted)] focus:border-white/16"
                />
              </label>

              <div className="flex flex-wrap gap-2">
                {filters.map((filter) => {
                  const active = activeFilter === filter;

                  return (
                    <button
                      key={filter}
                      type="button"
                      onClick={() => setActiveFilter(filter)}
                      className={`smooth-border rounded-full px-4 py-2 text-sm transition ${
                        active ? "bg-white text-black" : "bg-white/[0.03] text-[var(--muted)] hover:text-white"
                      }`}
                      style={{ ["--smooth-border-color" as string]: active ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.08)" }}
                    >
                      {filter}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>

          <div className="smooth-border overflow-hidden rounded-[2rem] bg-white/[0.025] p-3 shadow-[var(--shadow)]" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
            <div className="hidden md:block">
              <div className="grid grid-cols-[1.55fr_0.7fr_0.7fr] gap-4 px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                <div>Model</div>
                <div>Input / 1M</div>
                <div>Output / 1M</div>
              </div>
            </div>

            <div className="space-y-3">
              {filteredModels.map((model) => {
                const active = visibleSelection?.slug === model.slug;

                return (
                  <button
                    key={model.slug}
                    type="button"
                    onClick={() => setSelectedModel(model)}
                    className={`smooth-border grid w-full gap-4 rounded-[1.5rem] px-4 py-4 text-left transition md:grid-cols-[1.55fr_0.7fr_0.7fr] ${
                      active ? "bg-white text-black" : "bg-white/[0.035] text-white hover:bg-white/[0.05]"
                    }`}
                    style={{ ["--smooth-border-color" as string]: active ? "rgba(255,255,255,0.2)" : "rgba(255,255,255,0.08)" }}
                  >
                    <div>
                      <div className="font-[family-name:var(--font-heading)] text-lg">{model.name}</div>
                      <div className={`mt-1 text-xs uppercase tracking-[0.18em] ${active ? "text-black/60" : "text-[var(--muted)]"}`}>{model.category}</div>
                      {displayDiscount(model.slug) ? (
                        <div className={`mt-2 text-[11px] ${active ? "text-black/55" : "text-white/40"}`}>{displayDiscount(model.slug)}</div>
                      ) : null}
                    </div>
                    <div>
                      <div className={`text-[11px] uppercase tracking-[0.18em] md:hidden ${active ? "text-black/60" : "text-[var(--muted)]"}`}>Input / 1M</div>
                      <div className="mt-1 text-sm md:mt-0">{displayInputPrice(model.slug, model.inputPrice)}</div>
                    </div>
                    <div>
                      <div className={`text-[11px] uppercase tracking-[0.18em] md:hidden ${active ? "text-black/60" : "text-[var(--muted)]"}`}>Output / 1M</div>
                      <div className="mt-1 text-sm md:mt-0">{displayOutputPrice(model.slug, model.outputPrice)}</div>
                    </div>
                  </button>
                );
              })}

              {!filteredModels.length ? (
                <div className="rounded-[1.5rem] border border-white/8 bg-white/[0.03] px-4 py-8 text-center text-sm text-[var(--muted)]">
                  No models match your search.
                </div>
              ) : null}
            </div>
          </div>
        </div>

        <aside className="smooth-border rounded-[2rem] bg-white/[0.025] p-6 shadow-[var(--shadow)]" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
          {visibleSelection ? (
            <>
              <p className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Model details</p>
              <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl text-white">{visibleSelection.name}</h2>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-[var(--muted)]">{visibleSelection.category}</p>
              {displayDiscount(visibleSelection.slug) ? <p className="mt-2 text-xs text-white/50">{displayDiscount(visibleSelection.slug)}</p> : null}
              <p className="mt-5 text-sm leading-7 text-[var(--muted)]">{visibleSelection.description}</p>
              {visibleSelection.capabilities ? <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{visibleSelection.capabilities}</p> : null}

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <div className="smooth-border rounded-[1.25rem] bg-white/[0.03] p-4" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Input pricing</div>
                  <div className="mt-2 text-lg text-white">{displayInputPrice(visibleSelection.slug, visibleSelection.inputPrice)}</div>
                </div>
                <div className="smooth-border rounded-[1.25rem] bg-white/[0.03] p-4" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Output pricing</div>
                  <div className="mt-2 text-lg text-white">{displayOutputPrice(visibleSelection.slug, visibleSelection.outputPrice)}</div>
                </div>
              </div>

              <div className="mt-8 rounded-[1.5rem] border border-white/8 bg-[#0a0c0e] p-5">
                <div className="flex items-center justify-between gap-4">
                  <div className="text-xs uppercase tracking-[0.22em] text-[var(--muted)]">API model ID</div>
                  <button className="smooth-border rounded-full px-3 py-1 text-xs text-[var(--muted)] transition hover:text-white" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
                    Copy Model ID
                  </button>
                </div>
                <div className="mt-4 font-mono text-sm text-white">{visibleSelection.slug}</div>
                <pre className="mt-5 whitespace-pre-wrap break-words text-sm leading-7 text-[#d8dde6] [overflow-wrap:anywhere]">{`model="${visibleSelection.slug}"`}</pre>
              </div>
            </>
          ) : (
            <div className="text-sm text-[var(--muted)]">Select a model to view details.</div>
          )}
        </aside>
      </section>

      <section className="mt-16 flex flex-col items-center rounded-[2rem] border border-white/8 px-6 py-16 text-center shadow-[var(--shadow)] sm:px-10">
        <h2 className="font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">Ready to build?</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-[var(--muted)]">Use any available model through one API.</p>
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
