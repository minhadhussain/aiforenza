import { redirect } from "next/navigation";

import { DataTable } from "@/components/dashboard/data-table";
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
    <DataTable
      title="Transactions"
      description="Immutable ledger activity across trial credits, top-ups, and usage charges."
      rows={transactions}
      emptyMessage="No transactions yet. Wallet events will appear here as soon as they are created."
      columns={[
        { key: "date", label: "Date", render: (row) => formatDateLabel(row.created_at) },
        { key: "type", label: "Type", render: (row) => row.type },
        { key: "amount", label: "Amount", render: (row) => formatTransactionAmount(row.amount_cents) },
        { key: "balance", label: "Balance", render: (row) => formatUsdFromCents(row.balance_after_cents) },
        { key: "description", label: "Description", render: (row) => row.description },
      ]}
    />
  );
}
