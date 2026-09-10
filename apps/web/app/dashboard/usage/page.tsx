import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { apiGet } from "@/lib/api";
import type { ActivityPage } from "@/lib/activity";
import { UsageActivity } from "@/components/dashboard/usage-activity";

export default async function DashboardUsagePage() {
  const supabase = await createSupabaseServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) redirect("/login");
  const initial = await apiGet<ActivityPage>("/dashboard/activity", { accessToken: session.access_token, cache: "no-store" });
  return <UsageActivity key={initial.account.id} initial={initial} />;
}
