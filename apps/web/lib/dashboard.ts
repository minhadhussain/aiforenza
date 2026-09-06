import { apiGet } from "@/lib/api";

export type DashboardOverview = {
  profile: {
    id: string;
    email: string;
  };
  wallet: {
    id: string;
    user_id: string;
    balance_cents: number;
    currency: string;
    created_at: string;
    updated_at: string;
  } | null;
  transactions: Array<{
    id: string;
    type: string;
    amount_cents: number;
    balance_after_cents: number;
    description: string;
    reference_id: string | null;
    created_at: string;
  }>;
  metrics: {
    current_balance_cents: number;
    transaction_count: number;
    trial_credit_granted: boolean;
  };
  bootstrap: {
    trial_granted: boolean;
    wallet_id: string | null;
  };
};

export async function fetchDashboardOverview(accessToken: string) {
  return apiGet<DashboardOverview>("/dashboard/overview", {
    accessToken,
    cache: "no-store",
  });
}

export function formatUsdFromCents(value: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value / 100);
}

export function formatTransactionAmount(amountCents: number) {
  const prefix = amountCents >= 0 ? "+" : "-";
  return `${prefix}${formatUsdFromCents(Math.abs(amountCents))}`;
}

export function formatDateLabel(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(new Date(value));
}
