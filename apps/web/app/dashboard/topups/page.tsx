import { redirect } from "next/navigation";

export default async function DashboardTopupsRedirectPage() {
  redirect("/dashboard/billing");
}
