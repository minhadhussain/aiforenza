import { redirect } from "next/navigation";

import { fetchDashboardOverview } from "@/lib/dashboard";
import { formatDateLabel } from "@/lib/dashboard";
import { formatTransactionAmount } from "@/lib/dashboard";
import { formatUsdFromCents } from "@/lib/dashboard";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const overview = await fetchDashboardOverview(session.access_token);

  const cards = [
    {
      title: "Balance",
      value: formatUsdFromCents(overview.metrics.current_balance_cents),
      detail: overview.bootstrap.trial_granted
        ? "The $5 trial credit has just been granted to this account."
        : "Your wallet balance is loaded from the transaction ledger.",
    },
    {
      title: "Transactions",
      value: overview.metrics.transaction_count.toString(),
      detail: "Immutable ledger entries are the source of truth for wallet balance.",
    },
    {
      title: "Trial status",
      value: overview.metrics.trial_credit_granted ? "Granted" : "Pending",
      detail: "The signup credit uses an idempotent reference so duplicate grants are prevented.",
    },
  ];

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
      <section className="rounded-[2rem] border border-[var(--border)] bg-[var(--surface)] p-6 shadow-[var(--shadow)] backdrop-blur">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Phase 6 status</p>
        <h2 className="mt-3 font-[family-name:var(--font-heading)] text-3xl">Wallet, API keys, models, and billing foundation</h2>
        <p className="mt-4 max-w-2xl text-base leading-8 text-[var(--muted)]">
          The authenticated flow now boots the wallet, grants the one-time trial, supports API-key issuance, exposes the model catalog through the API, and records billable usage through the financial ledger.
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
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Recent transactions</p>
        <div className="mt-4 space-y-4">
          {overview.transactions.length ? (
            overview.transactions.map((transaction) => (
              <article key={transaction.id} className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-sm uppercase tracking-[0.15em] text-[var(--muted)]">{transaction.type}</p>
                    <h3 className="mt-2 font-[family-name:var(--font-heading)] text-lg">{transaction.description}</h3>
                    <p className="mt-2 text-sm text-[var(--muted)]">{formatDateLabel(transaction.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <div className="font-[family-name:var(--font-heading)] text-xl">{formatTransactionAmount(transaction.amount_cents)}</div>
                    <p className="mt-2 text-sm text-[var(--muted)]">
                      Balance {formatUsdFromCents(transaction.balance_after_cents)}
                    </p>
                  </div>
                </div>
              </article>
            ))
          ) : (
            <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
              No transactions yet. The first wallet bootstrap will create the free-trial ledger entry.
            </div>
          )}

          <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface-strong)] p-4 text-sm leading-6 text-[var(--muted)]">
            Next up from the spec: Stripe top-ups in Phase 7, richer dashboard surfaces in Phase 8, and developer docs in Phase 9.
          </div>
        </div>
      </section>
    </div>
  );
}
