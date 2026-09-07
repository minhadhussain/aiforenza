import Link from "next/link";

import { DeveloperTabs } from "@/components/home/developer-tabs";
import { MobileNav } from "@/components/home/mobile-nav";

const trustModels = ["GPT", "Claude", "Gemini", "Grok", "DeepSeek", "Kimi"];

const valueCards = [
  {
    title: "ONE API",
    copy: "One endpoint. Any model.",
  },
  {
    title: "ONE KEY",
    copy: "One key for everything.",
  },
  {
    title: "ONE BALANCE",
    copy: "Pay as you go.",
  },
];

const steps = [
  ["01", "SIGN UP", "Get started free."],
  ["02", "CREATE A KEY", "One secure API key."],
  ["03", "CONNECT", "Use your existing tools."],
  ["04", "BUILD", "Pay for what you use."],
] as const;

const modelRows = [
  ["GPT-6 Astra", "$X", "$Y"],
  ["GPT-5.6 Sol", "$X", "$Y"],
  ["GPT-5.6 Luna", "$X", "$Y"],
  ["Grok 4.6", "$X", "$Y"],
  ["DeepSeek V4 Pro", "$X", "$Y"],
  ["DeepSeek V4 Flash", "$X", "$Y"],
  ["Kimi K2.7 Code", "$X", "$Y"],
  ["GPT-5.4", "$X", "$Y"],
] as const;

const prepaidAmounts = ["$10", "$25", "$50", "$100", "$500", "$1,000"];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-[1200px] flex-col px-4 pb-20 pt-5 sm:px-6 lg:px-8">
      <header className="sticky top-0 z-20 mb-14">
        <div className="rounded-full border border-white/8 bg-black/35 px-4 py-3 shadow-[var(--shadow)] backdrop-blur-md sm:px-5">
          <div className="flex items-center justify-between gap-4">
            <Link href="/" className="font-[family-name:var(--font-heading)] text-base font-semibold tracking-[-0.035em] text-white sm:text-[1.06rem]">
              AI Forenza
            </Link>

            <nav className="hidden items-center gap-7 text-sm text-[var(--muted)] lg:flex">
              <Link className="transition hover:text-white" href="/models">
                Models
              </Link>
              <Link className="transition hover:text-white" href="/pricing">
                Pricing
              </Link>
              <Link className="transition hover:text-white" href="/docs">
                Docs
              </Link>
              <a className="transition hover:text-white" href="#about">
                About
              </a>
            </nav>

            <div className="hidden items-center gap-3 sm:flex">
              <Link className="px-3 py-2 text-sm text-[var(--muted)] transition hover:text-white" href="/login">
                Log in
              </Link>
              <Link
                className="inline-flex items-center justify-center rounded-full bg-white px-4 py-2 text-sm font-semibold text-black transition hover:bg-white/90"
                href="/signup"
              >
                Start Free
              </Link>
            </div>

            <MobileNav />
          </div>
        </div>
      </header>

      <section className="relative flex min-h-[78vh] flex-col items-center justify-center overflow-hidden rounded-[2.25rem] border border-white/6 px-6 py-20 text-center sm:px-10 lg:px-16">
        <div className="pointer-events-none absolute inset-0 opacity-70">
          <div className="absolute left-1/2 top-[18%] h-[360px] w-[360px] -translate-x-1/2 rounded-full bg-white/[0.06] blur-[120px]" />
          <div className="absolute left-[18%] top-[30%] h-40 w-px bg-gradient-to-b from-transparent via-white/20 to-transparent" />
          <div className="absolute right-[18%] top-[34%] h-40 w-px bg-gradient-to-b from-transparent via-white/20 to-transparent" />
          <div className="absolute left-1/2 top-[44%] h-px w-[52%] -translate-x-1/2 bg-gradient-to-r from-transparent via-white/10 to-transparent" />
          <div className="absolute left-1/2 top-[48%] h-px w-[36%] -translate-x-1/2 bg-gradient-to-r from-transparent via-white/8 to-transparent" />
        </div>

        <div className="relative z-10 flex max-w-4xl flex-col items-center">
          <div className="mb-8 inline-flex rounded-full border border-white/8 bg-white/[0.03] px-4 py-2 text-[11px] uppercase tracking-[0.22em] text-[var(--muted)]">
            Start free
          </div>

          <h1 className="max-w-4xl font-[family-name:var(--font-heading)] text-[3rem] leading-[0.95] tracking-[-0.05em] text-white sm:text-[4.5rem] lg:text-[6.25rem]">
            One API.
            <br />
            Multiple frontier models.
          </h1>

          <p className="mt-7 max-w-2xl text-base leading-8 text-[var(--muted)] sm:text-lg">
            Build with the models you want through one OpenAI-compatible API.
          </p>
          <p className="mt-2 max-w-2xl text-sm leading-7 text-white/46 sm:text-base">
            One key. Multiple models. Pay only for what you use.
          </p>

          <div className="mt-9 flex w-full max-w-md flex-col gap-3 sm:flex-row sm:justify-center">
            <Link
              className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-white/90"
              href="/signup"
            >
              Start Free →
            </Link>
            <Link
              className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.02] px-6 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.05]"
              href="/models"
            >
              View Models
            </Link>
          </div>
        </div>
      </section>

      <section className="mt-10 overflow-x-auto rounded-full border border-white/6 bg-white/[0.02] px-5 py-4 shadow-[var(--shadow)] backdrop-blur-sm">
        <div className="flex min-w-max items-center justify-between gap-8 text-xs uppercase tracking-[0.28em] text-white/45 sm:text-sm">
          {trustModels.map((model) => (
            <span key={model}>{model}</span>
          ))}
        </div>
      </section>

      <section id="about" className="mt-24 grid gap-8 lg:grid-cols-[0.92fr_1.08fr] lg:items-start">
        <div className="max-w-xl">
          <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">Value Proposition</p>
          <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl leading-tight text-white sm:text-4xl">
            One interface.
            <br />
            Every model you need.
          </h2>
          <p className="mt-5 text-base leading-8 text-[var(--muted)]">
            One API for every model.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          {valueCards.map((card) => (
            <article
              key={card.title}
              className="rounded-[1.75rem] border border-white/8 bg-white/[0.025] p-6 transition duration-300 hover:-translate-y-1 hover:border-white/14 hover:bg-white/[0.035]"
            >
              <p className="text-sm uppercase tracking-[0.24em] text-white/50">{card.title}</p>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{card.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-24">
        <div className="max-w-2xl">
          <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">How It Works</p>
          <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">From signup to first request.</h2>
        </div>

        <div className="mt-10 grid gap-4 lg:grid-cols-4">
          {steps.map(([index, title, copy]) => (
            <article key={index} className="relative rounded-[1.75rem] border border-white/8 bg-white/[0.025] p-6">
              <div className="mb-6 flex items-center justify-between">
                <span className="text-xs uppercase tracking-[0.3em] text-white/40">{index}</span>
                <span className="hidden h-px flex-1 bg-gradient-to-r from-white/12 to-transparent lg:block" />
              </div>
              <h3 className="font-[family-name:var(--font-heading)] text-xl text-white">{title}</h3>
              <p className="mt-4 text-sm leading-7 text-[var(--muted)]">{copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="mt-24 grid gap-10 lg:grid-cols-[0.9fr_1.1fr] lg:items-start">
        <div className="max-w-xl">
          <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">Developer Experience</p>
          <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">
            Works with the tools you already use.
          </h2>
          <p className="mt-5 text-base leading-8 text-[var(--muted)]">
            No new SDK. No new application architecture. Just an OpenAI-compatible endpoint.
          </p>
        </div>

        <DeveloperTabs />
      </section>

      <section className="mt-24">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">Model Catalog</p>
            <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">
              Choose the model. Keep the interface.
            </h2>
            <p className="mt-5 text-base leading-8 text-[var(--muted)]">
              Switch models without changing the way your application talks to the API.
            </p>
          </div>
          <Link className="text-sm text-white/72 transition hover:text-white" href="/models">
            View all models →
          </Link>
        </div>

        <div className="mt-8 overflow-x-auto rounded-[2rem] border border-white/8 bg-white/[0.025] p-3 shadow-[var(--shadow)]">
          <table className="min-w-full border-separate border-spacing-y-3 text-left text-sm">
            <thead>
              <tr>
                {[
                  ["Model", ""],
                  ["Input", "per 1M"],
                  ["Output", "per 1M"],
                ].map(([label, sublabel]) => (
                  <th key={label} className="px-4 py-2 font-semibold uppercase tracking-[0.16em] text-[var(--muted)]">
                    {label}
                    {sublabel ? <span className="ml-2 text-[10px] tracking-[0.18em] text-white/30">{sublabel}</span> : null}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {modelRows.map(([model, input, output]) => (
                <tr key={model} className="transition hover:translate-y-[-1px]">
                  <td className="rounded-l-2xl border-y border-l border-white/8 bg-white/[0.035] px-4 py-4 font-medium text-white">
                    {model}
                  </td>
                  <td className="border-y border-white/8 bg-white/[0.035] px-4 py-4 text-[var(--muted)]">{input}</td>
                  <td className="rounded-r-2xl border-y border-r border-white/8 bg-white/[0.035] px-4 py-4 text-[var(--muted)]">{output}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-24 grid gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:items-center">
        <div className="max-w-xl">
          <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">Pricing</p>
          <h2 className="mt-4 font-[family-name:var(--font-heading)] text-3xl text-white sm:text-4xl">Simple usage-based pricing.</h2>
          <p className="mt-5 whitespace-pre-line text-base leading-8 text-[var(--muted)]">
            {`$5 free credit to get started.
Then pay only for what you use.`}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          {prepaidAmounts.map((amount) => (
            <div
              key={amount}
              className="rounded-[1.6rem] border border-white/8 bg-white/[0.03] px-5 py-6 text-center transition hover:border-white/16 hover:bg-white/[0.05]"
            >
              <div className="font-[family-name:var(--font-heading)] text-3xl text-white">{amount}</div>
              <div className="mt-2 text-xs uppercase tracking-[0.22em] text-[var(--muted)]">Prepaid balance</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-24 rounded-[2.5rem] border border-white/8 px-6 py-20 text-center shadow-[var(--shadow)] sm:px-10">
        <div className="mx-auto max-w-3xl">
          <p className="text-sm uppercase tracking-[0.24em] text-[var(--muted)]">Start Building</p>
          <h2 className="mt-4 font-[family-name:var(--font-heading)] text-4xl leading-tight text-white sm:text-5xl">
            Start building with one API.
          </h2>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-8 text-[var(--muted)]">
            Get $5 in free API credit and make your first request in minutes.
          </p>
          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Link className="inline-flex items-center justify-center rounded-full bg-white px-6 py-3 text-sm font-semibold text-black transition hover:bg-white/90" href="/signup">
              Start with $5 Free →
            </Link>
            <Link className="inline-flex items-center justify-center rounded-full border border-white/10 bg-white/[0.02] px-6 py-3 text-sm font-semibold text-white transition hover:border-white/20 hover:bg-white/[0.05]" href="/docs">
              Read the Docs
            </Link>
          </div>
        </div>
      </section>

      <footer className="mt-24 flex flex-col gap-8 border-t border-white/8 py-10 text-sm text-[var(--muted)] sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="font-[family-name:var(--font-heading)] text-base text-white">AI Forenza</div>
          <p className="mt-2 max-w-sm leading-7">One API. Multiple frontier models.</p>
        </div>
        <div className="flex flex-wrap gap-5">
          {[
            ["Models", "/models"],
            ["Pricing", "/pricing"],
            ["Docs", "/docs"],
            ["API", "/docs"],
            ["Status", "/status"],
            ["Terms", "/terms"],
            ["Privacy", "/privacy"],
          ].map(([label, href]) => (
            <Link key={label} className="transition hover:text-white" href={href}>
              {label}
            </Link>
          ))}
        </div>
      </footer>
    </main>
  );
}
