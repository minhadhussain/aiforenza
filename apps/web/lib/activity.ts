export type ActivityRecord = {
  request_id: string; created_at: string;
  status: "billed" | "unsettled" | "rejected" | "released";
  api_key_id: string; api_key_name: string | null;
  model_slug: string | null; model_name: string | null;
  input_tokens: number | null; output_tokens: number | null; cached_input_tokens: number | null;
  customer_charge_cents: number | null; reference_charge_cents: number | null;
  customer_savings_cents: number | null; reserved_cents: number;
  error_code: string | null; http_status: number | null;
};
export type ActivityPage = {
  data: ActivityRecord[]; total: number; page: number; page_size: number; as_of: string;
  account: { id: string; email: string };
  models: { slug: string; name: string }[];
  keys: { id: string; name: string }[];
};
