import { redirect } from "next/navigation";

import { DataTable } from "@/components/dashboard/data-table";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchDashboardUsage, formatDateLabel, formatUsdFromCents } from "@/lib/dashboard";

export default async function DashboardUsagePage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const records = await fetchDashboardUsage(session.access_token);

  return (
    <DataTable
      title="Usage"
      description="Basic request-level usage records captured after billable model requests."
      rows={records}
      emptyMessage="No usage yet. Your first successful API request will appear here."
      columns={[
        { key: "date", label: "Date", render: (row) => formatDateLabel(row.created_at) },
        { key: "model", label: "Model", render: (row) => row.model?.display_name ?? row.model?.slug ?? "Unknown" },
        { key: "input", label: "Input", render: (row) => row.input_tokens.toLocaleString() },
        { key: "output", label: "Output", render: (row) => row.output_tokens.toLocaleString() },
        { key: "cost", label: "Cost", render: (row) => formatUsdFromCents(row.customer_charge_cents) },
        { key: "status", label: "Status", render: (row) => row.status },
      ]}
    />
  );
}
