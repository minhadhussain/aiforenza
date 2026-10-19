import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { build2026Fonts } from "@/components/build-2026/fonts";
import { Build2026Panel } from "@/components/dashboard/build-2026-panel";
import { apiGet } from "@/lib/api";
import type { HackathonStatus } from "@/lib/hackathon";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "BUILD 2026 Credits | AI Forenza",
  description: "Claim your selected BUILD 2026 project's AI Forenza credits. Connect your tools and build something real at Hackyard BUILD 2026.",
};

export default async function Build2026Page() {
  const supabase = await createSupabaseServerClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (!session) redirect("/login");
  const initial = await apiGet<HackathonStatus>("/hackathon/status", { accessToken: session.access_token, cache: "no-store" });
  return <div className={build2026Fonts}><Build2026Panel key={session.user.id} initial={initial} userId={session.user.id} /></div>;
}
