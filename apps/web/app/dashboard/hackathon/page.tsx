import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { apiGet } from "@/lib/api";
import type { HackathonStatus } from "@/lib/hackathon";
import { HackathonPanel } from "@/components/dashboard/hackathon-panel";

export default async function HackathonPage() {
  const supabase = await createSupabaseServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");
  const initial = await apiGet<HackathonStatus>("/hackathon/status", { accessToken: session.access_token, cache: "no-store" });
  return <HackathonPanel key={session.user.id} initial={initial} userId={session.user.id} />;
}
