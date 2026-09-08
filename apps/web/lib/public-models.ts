import { apiGet } from "@/lib/api";
import type { DashboardModel } from "@/lib/dashboard";

export async function fetchPublicModels() {
  const payload = await apiGet<{ data: DashboardModel[] }>("/public/models", {
    accessToken: "public-catalog",
    cache: "no-store",
  });

  return payload.data;
}
