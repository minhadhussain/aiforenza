import Link from "next/link";

import { PublicShell } from "@/components/home/public-shell";
import { SectionHero } from "@/components/home/section-hero";

const docsSections = [
  ["Introduction", "Understand the platform, API shape, wallet model, and supported clients."],
  ["Quickstart", "Go from signup to API key to first request in a few minutes."],
  ["Authentication", "Use one API key for OpenAI-compatible requests and dashboard auth for account access."],
  ["Models", "Browse the available models and keep the same integration surface."],
  ["Chat Completions", "Send standard OpenAI-style chat requests through the unified API."],
  ["Streaming", "Use streamed responses for coding agents and real-time UX."],
  ["Claude Code", "Configure AI Forenza as an OpenAI-compatible backend for coding workflows."],
  ["OpenCode", "Connect your local tooling without changing the request architecture."],
  ["Python", "Use the OpenAI SDK with a custom `base_url` and your AI Forenza key."],
  ["JavaScript", "Use the same OpenAI-compatible flow from Node or frontend-safe server wrappers."],
  ["Errors", "Handle normalized API errors such as invalid API keys, insufficient balance, or model not found."],
  ["Usage & Billing", "Understand wallet deduction, usage records, and prepaid top-ups."],
] as const;

const quickstartCode = `from openai import OpenAI\n\nclient = OpenAI(\n    api_key="YOUR_API_KEY",\n    base_url="https://api.yourdomain.com/v1"\n)\n\nresponse = client.chat.completions.create(\n    model="gpt-5.6-luna",\n    messages=[\n        {"role": "user", "content": "Hello"}\n    ]\n)\n\nprint(response.choices[0].message.content)`;

export default function DocsPage() {
  return (
    <PublicShell>
      <SectionHero
        eyebrow="Docs"
        title="From signup to first request."
        copy="AI Forenza documentation is structured to get developers from free credit to a working OpenAI-compatible request path quickly."
      />

      <section className="mt-14 grid gap-4 lg:grid-cols-[0.9fr_1.1fr]">
        <div className="rounded-[2rem] border border-white/8 bg-white/[0.025] p-6 shadow-[var(--shadow)]">
          <p className="text-sm uppercase tracking-[0.22em] text-[var(--muted)]">Quickstart</p>
          <ol className="mt-5 space-y-4 text-sm leading-7 text-[var(--muted)]">
            <li>1. Create an account and receive free API credit.</li>
            <li>2. Generate an API key from your dashboard.</li>
            <li>3. Point your existing OpenAI-compatible client to `https://api.yourdomain.com/v1`.</li>
            <li>4. Choose a model and send your first request.</li>
          </ol>

          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link className="inline-flex items-center justify-center rounded-full bg-white px-5 py-3 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
              Start Free
            </Link>
            <Link className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.02] px-5 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.05]" href="/models">
              Browse Models
            </Link>
          </div>
        </div>

        <div className="rounded-[2rem] border border-white/8 bg-[#090b0d] p-6 shadow-[var(--shadow)]">
          <div className="flex items-center justify-between gap-4">
            <p className="text-sm uppercase tracking-[0.22em] text-[var(--muted)]">Python Example</p>
            <button className="rounded-full border border-white/8 px-3 py-1 text-xs text-[var(--muted)] transition hover:border-white/16 hover:text-white">Copy</button>
          </div>
          <pre className="mt-5 overflow-x-auto whitespace-pre-wrap text-sm leading-7 text-[#edf1f7]">{quickstartCode}</pre>
        </div>
      </section>

      <section className="mt-16 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {docsSections.map(([title, copy]) => (
          <article key={title} className="rounded-[1.75rem] border border-white/8 bg-white/[0.025] p-6 transition hover:border-white/14 hover:bg-white/[0.035]">
            <h2 className="font-[family-name:var(--font-heading)] text-xl text-white">{title}</h2>
            <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{copy}</p>
          </article>
        ))}
      </section>
    </PublicShell>
  );
}
