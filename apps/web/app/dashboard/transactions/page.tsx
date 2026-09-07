import { redirect } from "next/navigation";

import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchDashboardTransactions, formatDateLabel, formatTransactionAmount, formatUsdFromCents } from "@/lib/dashboard";

export default async function DashboardTransactionsPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const transactions = await fetchDashboardTransactions(session.access_token);

  return (
    <div className="space-y-8">
      <header>
        <p className="font-mono text-sm uppercase tracking-[0.16em] text-white/70">// TRANSACTIONS</p>
        <p className="mt-3 text-sm leading-7 text-[var(--muted)]">Immutable ledger activity for trial credit, top-ups, refunds, adjustments, and usage.</p>
      </header>

      <section className="border border-white/10 bg-[#050608] p-4">
        {transactions.length ? (
          <div className="space-y-2">
            <div className="grid gap-3 border-b border-white/10 px-3 py-2 text-xs uppercase tracking-[0.14em] text-[var(--muted)] md:grid-cols-[0.9fr_0.8fr_0.9fr_0.9fr_1.2fr]">
              <div>DATE</div>
              <div>TYPE</div>
              <div>AMOUNT</div>
              <div>BALANCE</div>
              <div>DESCRIPTION</div>
            </div>

            {transactions.map((transaction) => (
              <div key={transaction.id} className="grid gap-3 border border-white/10 px-3 py-3 text-sm md:grid-cols-[0.9fr_0.8fr_0.9fr_0.9fr_1.2fr]">
                <div className="text-[var(--muted)]">{formatDateLabel(transaction.created_at).toUpperCase()}</div>
                <div className="text-white">{transaction.type}</div>
                <div className="text-[var(--muted)]">{formatTransactionAmount(transaction.amount_cents)}</div>
                <div className="text-[var(--muted)]">{formatUsdFromCents(transaction.balance_after_cents)}</div>
                <div className="text-[var(--muted)]">{transaction.description}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="border border-white/10 px-4 py-4 text-sm text-[var(--muted)]">No transactions yet.</div>
        )}
      </section>
    </div>
  );
}
