import { apiGet } from "@/lib/api";

export type ApiKeyRecord = {
  id: string;
  name: string;
  key_prefix: string;
  masked_key: string;
  last_used_at: string | null;
  created_at: string;
  revoked_at: string | null;
  status: "active" | "revoked";
};

export async function fetchApiKeys(accessToken: string) {
  const payload = await apiGet<{ data: ApiKeyRecord[] }>("/api-keys", {
    accessToken,
    cache: "no-store",
  });

  return payload.data;
}
