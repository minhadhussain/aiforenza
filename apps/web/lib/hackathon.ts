export type HackathonGrant = {
  team_id: string; campaign_name: string; status: string;
  promo_balance_cents: number; reserved_cents: number; available_balance_cents: number;
  claimed_at?: string; key_revoked?: boolean; billing_source: "PROMOTIONAL";
};
export type HackathonStatus = {
  campaign: { name: string; grant_amount_cents: number } | null;
  grants: HackathonGrant[];
};
