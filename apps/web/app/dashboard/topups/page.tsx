import { redirect } from "next/navigation";

import { TopupPanel } from "@/components/dashboard/topup-panel";
import { fetchDashboardOverview } from "@/lib/dashboard";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { fetchTopups } from "@/lib/topups";

export default async function DashboardTopupsPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const [overview, topups] = await Promise.all([
    fetchDashboardOverview(session.access_token),
    fetchTopups(session.access_token),
  ]);

  return (
    <TopupPanel
      accessToken={session.access_token}
      balanceCents={overview.metrics.current_balance_cents}
      initialTopups={topups}
    />
  );
}
