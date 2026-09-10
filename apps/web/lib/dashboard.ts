import { apiGet } from "@/lib/api";
import { fetchApiKeys } from "@/lib/api-keys";

export type DashboardOverview = {
  profile: {
    id: string;
    email: string;
  };
  wallet: {
    id: string;
    user_id: string;
    balance_cents: number;
    available_balance_cents: number;
    reserved_cents: number;
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
    available_balance_cents: number;
    reserved_cents: number;
    transaction_count: number;
    trial_credit_granted: boolean;
    today_usage_cents: number;
    month_usage_cents: number;
    api_request_count: number;
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
  total_tokens: number;
  reference_charge_cents: number | null;
  customer_charge_cents: number;
  customer_savings_cents: number | null;
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
  reference_input_price_per_million: string;
  reference_output_price_per_million: string;
  reference_cached_input_price_per_million: string | null;
  discount_percent: string;
  customer_input_price_per_million: string;
  customer_output_price_per_million: string;
  customer_cached_input_price_per_million: string | null;
  pricing_basis: string;
  reference_price_source: string | null;
  pricing_max_input_tokens: number;
  pricing_max_output_tokens: number;
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

export async function fetchDashboardApiKeys(accessToken: string) {
  return fetchApiKeys(accessToken);
}

export function formatUsdFromCents(value: number | null) {
  if (value === null) return "Not recorded";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(value / 100);
}

export function formatModelRate(value: string | number | null) {
  if (value === null || !Number.isFinite(Number(value))) return "Not configured";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2, maximumFractionDigits: 6 }).format(Number(value));
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
