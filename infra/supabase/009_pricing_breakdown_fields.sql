alter table public.models
  add column if not exists discount_percent numeric(5,2);

update public.models
set discount_percent = coalesce(discount_percent, 40)
where discount_percent is null;

alter table public.models
  alter column discount_percent set not null,
  alter column discount_percent set default 40;

alter table public.usage_records
  add column if not exists reference_charge_cents bigint,
  add column if not exists customer_savings_cents bigint,
  add column if not exists provider_cost_cents bigint,
  add column if not exists total_tokens integer;

update public.usage_records
set
  reference_charge_cents = coalesce(reference_charge_cents, customer_charge_cents),
  customer_savings_cents = coalesce(customer_savings_cents, 0),
  total_tokens = coalesce(total_tokens, input_tokens + output_tokens + cached_input_tokens)
where reference_charge_cents is null
   or customer_savings_cents is null
   or total_tokens is null;
