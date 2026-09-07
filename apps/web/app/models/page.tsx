"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import { PublicShell } from "@/components/home/public-shell";
import { SectionHero } from "@/components/home/section-hero";

type ModelCategory = "All" | "General" | "Reasoning" | "Coding";

type ModelRecord = {
  name: string;
  slug: string;
  category: Exclude<ModelCategory, "All">;
  inputPrice: string;
  outputPrice: string;
  description: string;
  capabilities?: string;
};

const models: ModelRecord[] = [
  {
    name: "GPT-6 Astra",
    slug: "gpt-6-astra",
    category: "General",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "General-purpose frontier model for broad production workloads.",
    capabilities: "Strong default choice for multi-step generation and broad reasoning tasks.",
  },
  {
    name: "GPT-5.6 Sol",
    slug: "gpt-5.6-sol",
    category: "General",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "Balanced general model for everyday developer-facing inference.",
    capabilities: "Good tradeoff between latency and reasoning depth.",
  },
  {
    name: "GPT-5.6 Luna",
    slug: "gpt-5.6-luna",
    category: "General",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "General model tuned for OpenAI-compatible workflows and agent loops.",
    capabilities: "Fits common SDK and coding-assistant integrations.",
  },
  {
    name: "Grok 4.6",
    slug: "grok-4.6",
    category: "General",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "General conversational model with a distinct inference profile.",
    capabilities: "Useful when you want a different model family behind the same interface.",
  },
  {
    name: "DeepSeek V4 Pro",
    slug: "deepseek-v4-pro",
    category: "Reasoning",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "Reasoning-oriented model for deeper analytical tasks.",
    capabilities: "Well suited to heavier technical and structured reasoning workflows.",
  },
  {
    name: "DeepSeek V4 Flash",
    slug: "deepseek-v4-flash",
    category: "Reasoning",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "Faster reasoning variant for lighter latency-sensitive requests.",
    capabilities: "Good for quicker responses while keeping a reasoning-first profile.",
  },
  {
    name: "Kimi K2.7 Code",
    slug: "kimi-k2.7-code",
    category: "Coding",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "Coding-focused model for implementation and editor workflows.",
    capabilities: "Useful for code generation, iteration, and development assistants.",
  },
  {
    name: "GPT-5.4",
    slug: "gpt-5.4",
    category: "General",
    inputPrice: "$X",
    outputPrice: "$Y",
    description: "Stable general model for predictable, standard request patterns.",
    capabilities: "Works well as a dependable fallback in a shared integration surface.",
  },
];

const filters: ModelCategory[] = ["All", "General", "Reasoning", "Coding"];

export default function ModelsPage() {
  const [search, setSearch] = useState("");
  const [activeFilter, setActiveFilter] = useState<ModelCategory>("All");
  const [selectedModel, setSelectedModel] = useState<ModelRecord | null>(models[0]);

  const filteredModels = useMemo(() => {
    const normalized = search.trim().toLowerCase();

    return models.filter((model) => {
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
                    </div>
                    <div>
                      <div className={`text-[11px] uppercase tracking-[0.18em] md:hidden ${active ? "text-black/60" : "text-[var(--muted)]"}`}>Input / 1M</div>
                      <div className="mt-1 text-sm md:mt-0">{model.inputPrice}</div>
                    </div>
                    <div>
                      <div className={`text-[11px] uppercase tracking-[0.18em] md:hidden ${active ? "text-black/60" : "text-[var(--muted)]"}`}>Output / 1M</div>
                      <div className="mt-1 text-sm md:mt-0">{model.outputPrice}</div>
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
              <p className="mt-5 text-sm leading-7 text-[var(--muted)]">{visibleSelection.description}</p>
              {visibleSelection.capabilities ? <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{visibleSelection.capabilities}</p> : null}

              <div className="mt-8 grid gap-3 sm:grid-cols-2">
                <div className="smooth-border rounded-[1.25rem] bg-white/[0.03] p-4" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Input pricing</div>
                  <div className="mt-2 text-lg text-white">{visibleSelection.inputPrice}</div>
                </div>
                <div className="smooth-border rounded-[1.25rem] bg-white/[0.03] p-4" style={{ ["--smooth-border-color" as string]: "rgba(255,255,255,0.08)" }}>
                  <div className="text-xs uppercase tracking-[0.18em] text-[var(--muted)]">Output pricing</div>
                  <div className="mt-2 text-lg text-white">{visibleSelection.outputPrice}</div>
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
