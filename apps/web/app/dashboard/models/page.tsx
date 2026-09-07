import { redirect } from "next/navigation";

import { DataTable } from "@/components/dashboard/data-table";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchDashboardModels, formatUsdFromCents } from "@/lib/dashboard";

function perMillionToCents(value: number | null) {
  return value ?? 0;
}

export default async function DashboardModelsPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const models = await fetchDashboardModels(session.access_token);

  return (
    <DataTable
      title="Models"
      description="Enabled customer-facing models and their current pricing configuration."
      rows={models}
      emptyMessage="No enabled models are available yet."
      columns={[
        { key: "model", label: "Model", render: (row) => row.display_name },
        { key: "provider", label: "Provider", render: (row) => row.provider },
        { key: "input", label: "Input / 1M", render: (row) => formatUsdFromCents(perMillionToCents(row.customer_input_price_per_million * 100)) },
        { key: "output", label: "Output / 1M", render: (row) => formatUsdFromCents(perMillionToCents(row.customer_output_price_per_million * 100)) },
        { key: "cached", label: "Cached / 1M", render: (row) => formatUsdFromCents(perMillionToCents((row.customer_cached_input_price_per_million ?? 0) * 100)) },
      ]}
    />
  );
}
