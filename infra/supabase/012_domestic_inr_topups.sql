alter table public.topups
  add column if not exists package_id text,
  add column if not exists package_value_usd_cents bigint,
  add column if not exists stripe_amount_inr bigint,
  add column if not exists exchange_rate_used numeric(12,6),
  add column if not exists cancellation_reason text;

update public.topups
set
  package_id = coalesce(package_id, 'legacy_topup'),
  package_value_usd_cents = coalesce(package_value_usd_cents, amount_cents),
  stripe_amount_inr = coalesce(stripe_amount_inr, amount_cents),
  exchange_rate_used = coalesce(exchange_rate_used, 1)
where package_id is null or package_value_usd_cents is null or stripe_amount_inr is null or exchange_rate_used is null;

alter table public.topups
  alter column package_id set not null,
  alter column package_value_usd_cents set not null,
  alter column stripe_amount_inr set not null,
  alter column exchange_rate_used set not null;
