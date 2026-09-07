import { apiGet } from "@/lib/api";

export type TopupRecord = {
  id: string;
  amount_cents: number;
  currency: string;
  status: "PENDING" | "COMPLETED" | "FAILED" | "REFUNDED";
  created_at: string;
  completed_at: string | null;
  stripe_checkout_session_id: string;
};

export async function fetchTopups(accessToken: string) {
  const payload = await apiGet<{ data: TopupRecord[] }>("/topups", {
    accessToken,
    cache: "no-store",
  });

  return payload.data;
}
