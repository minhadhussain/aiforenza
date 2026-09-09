import { apiGet } from "@/lib/api";
import type { DashboardModel } from "@/lib/dashboard";

export async function fetchPublicModels() {
  const payload = await apiGet<{ data: DashboardModel[] }>("/public/models", {
    cache: "no-store",
  });

  return payload.data;
}
