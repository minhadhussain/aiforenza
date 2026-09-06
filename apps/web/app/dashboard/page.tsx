const cards = [
  {
    title: "Balance",
    value: "$5.00",
    detail: "Trial credit display will become live in the wallet phase.",
  },
  {
    title: "API Keys",
    value: "0 active",
    detail: "Creation and revocation arrive in Phase 4.",
  },
  {
    title: "Usage",
    value: "0 requests",
    detail: "Usage records and billing are added after the model API is in place.",
  },
];

export default function DashboardPage() {
  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Phase 2 status</p>
        <h2 className="mt-3 font-[family-name:var(--font-heading)] text-3xl">Authentication is wired in</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-[var(--muted)]">
          This protected dashboard confirms the Supabase session flow works across browser login, middleware refresh, and server-rendered route protection.
        </p>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          {cards.map((card) => (
            <article key={card.title} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-5">
              <p className="text-sm uppercase tracking-[0.15em] text-[var(--muted)]">{card.title}</p>
              <div className="mt-3 font-[family-name:var(--font-heading)] text-3xl">{card.value}</div>
              <p className="mt-3 text-sm leading-6 text-[var(--muted)]">{card.detail}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Next milestones</p>
        <div className="mt-4 space-y-4">
          {[
            "Create the application profile row for new users.",
            "Grant the $5 trial credit transactionally.",
            "Add protected API key management screens.",
            "Connect dashboard cards to live wallet and usage data.",
          ].map((item) => (
            <div key={item} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
              {item}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
