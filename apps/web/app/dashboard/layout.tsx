import { redirect } from "next/navigation";

import { DashboardShell } from "@/components/dashboard/dashboard-shell";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { accountSetupPath, isTemporaryAuthError } from "@/lib/auth";

export default async function DashboardLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const supabase = await createSupabaseServerClient();
  const result = await supabase.auth.getUser().catch(() => null);
  if (!result || isTemporaryAuthError(result.error)) {
    redirect(accountSetupPath("/dashboard", true));
  }
  const user = result.data.user;

  if (!user) {
    redirect("/login");
  }

  return <DashboardShell email={user.email ?? "unknown-user"}>{children}</DashboardShell>;
}
