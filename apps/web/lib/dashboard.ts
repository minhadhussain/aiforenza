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

export type DashboardTransaction = {
  id: string;
  type: string;
  amount_cents: number;
  balance_after_cents: number;
  description: string;
  reference_id: string | null;
  created_at: string;
};

export type DashboardUsageRecord = {
  id: string;
  request_id: string;
  input_tokens: number;
  output_tokens: number;
  cached_input_tokens: number;
  customer_charge_cents: number;
  status: string;
  created_at: string;
  model: {
    slug: string;
    display_name: string;
  } | null;
};

export type DashboardModel = {
  id: string;
  slug: string;
  display_name: string;
  provider: string;
  customer_input_price_per_million: number;
  customer_output_price_per_million: number;
  customer_cached_input_price_per_million: number | null;
};

export async function fetchDashboardOverview(accessToken: string) {
  return apiGet<DashboardOverview>("/dashboard/overview", {
    accessToken,
    cache: "no-store",
  });
}

export async function fetchDashboardTransactions(accessToken: string) {
  const payload = await apiGet<{ data: DashboardTransaction[] }>("/dashboard/transactions", {
    accessToken,
    cache: "no-store",
  });

  return payload.data;
}

export async function fetchDashboardUsage(accessToken: string) {
  const payload = await apiGet<{ data: DashboardUsageRecord[] }>("/dashboard/usage", {
    accessToken,
    cache: "no-store",
  });

  return payload.data;
}

export async function fetchDashboardModels(accessToken: string) {
  const payload = await apiGet<{ data: DashboardModel[] }>("/dashboard/models", {
    accessToken,
    cache: "no-store",
  });

  return payload.data;
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
