const stats = [
  { label: "Trial credit", value: "$5", detail: "Granted automatically on signup" },
  { label: "Primary API", value: "/v1/chat/completions", detail: "OpenAI-compatible request format" },
  { label: "Model routing", value: "LiteLLM", detail: "Config-driven provider mapping" },
];

const sections = [
  {
    title: "Sign up and get moving",
    copy: "Create an account, receive free credit, mint an API key, and make the first request without learning a custom integration model.",
  },
  {
    title: "Top up when usage becomes real",
    copy: "Use prepaid Stripe Checkout balances instead of subscriptions so the commercial path stays simple and easy to understand.",
  },
  {
    title: "Keep pricing and model access configurable",
    copy: "Customer pricing, enabled models, and provider deployment mappings stay owned by the platform, not buried inside provider glue.",
  },
];

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-8 sm:px-10 lg:px-12">
      <header className="mb-12 flex items-center justify-between rounded-full border border-[var(--border)] bg-[var(--surface)] px-5 py-3 shadow-[var(--shadow)] backdrop-blur">
        <div>
          <div className="font-[family-name:var(--font-heading)] text-sm uppercase tracking-[0.3em] text-[var(--muted)]">
            AI Credit Platform
          </div>
        </div>
        <nav className="hidden gap-6 text-sm text-[var(--muted)] md:flex">
          <a href="#product">Product</a>
          <a href="#journey">Journey</a>
          <a href="#stack">Stack</a>
        </nav>
      </header>

      <section className="grid gap-8 lg:grid-cols-[1.3fr_0.9fr] lg:items-center">
        <div className="space-y-6">
          <p className="inline-flex rounded-full border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm text-[var(--muted)] shadow-[var(--shadow)]">
            OpenAI-compatible access for developers and research teams
          </p>
          <div className="space-y-4">
            <h1 className="max-w-4xl font-[family-name:var(--font-heading)] text-5xl leading-none sm:text-6xl lg:text-7xl">
              One API. Multiple frontier models.
            </h1>
            <p className="max-w-2xl text-lg leading-8 text-[var(--muted)] sm:text-xl">
              Build with the models you want through one prepaid API, with trial credit, wallet-backed usage, and a minimal dashboard for keys, usage, and top-ups.
            </p>
          </div>
          <div className="flex flex-col gap-4 sm:flex-row">
            <a className="inline-flex items-center justify-center rounded-full bg-[var(--accent)] px-6 py-3 text-base font-semibold text-white transition hover:bg-[var(--accent-strong)]" href="#journey">
              Start with $5 Free
            </a>
            <a className="inline-flex items-center justify-center rounded-full border border-[var(--border)] bg-[var(--surface)] px-6 py-3 text-base font-semibold text-[var(--text)]" href="#stack">
              View Foundations
            </a>
          </div>
        </div>

        <div className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Launch snapshot</p>
              <h2 className="font-[family-name:var(--font-heading)] text-2xl">MVP focus</h2>
            </div>
            <span className="rounded-full bg-[var(--bg-strong)] px-3 py-1 text-sm font-medium text-[var(--accent-strong)]">Phase 1</span>
          </div>
          <div className="space-y-4">
            {stats.map((item) => (
              <div key={item.label} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4">
                <div className="text-sm text-[var(--muted)]">{item.label}</div>
                <div className="mt-1 font-[family-name:var(--font-heading)] text-2xl">{item.value}</div>
                <div className="mt-2 text-sm leading-6 text-[var(--muted)]">{item.detail}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="journey" className="mt-16 rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur sm:p-8">
        <div className="mb-8 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Core Journey</p>
            <h2 className="font-[family-name:var(--font-heading)] text-3xl">The smallest usable revenue loop</h2>
          </div>
          <p className="max-w-xl text-sm leading-6 text-[var(--muted)]">
            Visitor to signup, trial credit, API key creation, first request, low-balance prompt, Stripe top-up, and continued usage.
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {sections.map((section) => (
            <article key={section.title} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-5">
              <h3 className="font-[family-name:var(--font-heading)] text-xl">{section.title}</h3>
              <p className="mt-3 text-sm leading-7 text-[var(--muted)]">{section.copy}</p>
            </article>
          ))}
        </div>
      </section>

      <section id="stack" className="mt-16 grid gap-4 pb-10 md:grid-cols-2 xl:grid-cols-4">
        {[
          ["Frontend", "Next.js, TypeScript, Tailwind CSS, shadcn/ui-ready structure"],
          ["Backend", "FastAPI, Pydantic settings, modular API package layout"],
          ["Platform", "Supabase, Redis, LiteLLM, Stripe, Caddy, Docker Compose"],
          ["Guardrails", "Integer-cent billing, API key hashing, atomic wallet planning, explicit env boundaries"],
        ].map(([title, copy]) => (
          <div key={title} className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-5 shadow-[var(--shadow)]">
            <div className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">{title}</div>
            <p className="mt-3 text-base leading-7 text-[var(--text)]">{copy}</p>
          </div>
        ))}
      </section>
    </main>
  );
}
