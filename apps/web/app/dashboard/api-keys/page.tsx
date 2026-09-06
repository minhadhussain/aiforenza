import { redirect } from "next/navigation";

import { ApiKeyPanel } from "@/components/dashboard/api-key-panel";
import { fetchApiKeys } from "@/lib/api-keys";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export default async function DashboardApiKeysPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    redirect("/login");
  }

  const keys = await fetchApiKeys(session.access_token);

  return <ApiKeyPanel initialKeys={keys} accessToken={session.access_token} />;
}
