-- Correct current configuration only; no historical charges or wallet balances change.
begin;
create table public.model_configuration_audit (
  id bigint generated always as identity primary key,
  model_id uuid not null,
  previous_configuration jsonb not null,
  reason text not null,
  created_at timestamptz not null default now()
);
alter table public.model_configuration_audit enable row level security;
revoke all on public.model_configuration_audit from public,anon,authenticated;
grant select on public.model_configuration_audit to service_role;
insert into public.model_configuration_audit(model_id,previous_configuration,reason)
select id,to_jsonb(m),'Remove verification aliases/test prices; adopt sourced standard text benchmark rates'
from public.models m;

alter table public.models
  add column reference_price_source text,
  add column reference_price_checked_at timestamptz,
  add column reference_price_valid_until timestamptz,
  add column pricing_verified boolean not null default false,
  add column availability_note text,
  add column pricing_max_input_tokens integer not null default 190000,
  add column pricing_max_output_tokens integer not null default 32768,
  add column provider_input_cost_per_million numeric(18,8),
  add column provider_output_cost_per_million numeric(18,8),
  add column provider_cached_input_cost_per_million numeric(18,8),
  add column provider_cost_source text;

-- NULL means unconfigured, not free. Remove misleading zero/test defaults.
alter table public.models
  alter column input_price_per_million drop not null,
  alter column output_price_per_million drop not null,
  alter column customer_input_price_per_million drop not null,
  alter column customer_output_price_per_million drop not null,
  alter column input_price_per_million drop default,
  alter column output_price_per_million drop default,
  alter column cached_input_price_per_million drop default,
  alter column customer_input_price_per_million drop default,
  alter column customer_output_price_per_million drop default,
  alter column customer_cached_input_price_per_million drop default,
  alter column enabled set default false;

update public.models set enabled=false, pricing_verified=false,
  input_price_per_million=null, output_price_per_million=null, cached_input_price_per_million=null,
  customer_input_price_per_million=null, customer_output_price_per_million=null, customer_cached_input_price_per_million=null,
  availability_note='Unavailable until inference and reference pricing are verified',updated_at=now();

-- These public IDs identify the same model upstream; never substitute Sol for Luna.
update public.models set provider_model_id=case slug
  when 'deepseek-v4-pro' then 'DeepSeek-V4-Pro'
  when 'deepseek-v4-flash' then 'DeepSeek-V4-Flash'
  when 'kimi-k2.7-code' then 'Kimi-K2.7-Code'
  else slug end
where provider='azure' and slug in ('gpt-6-astra','gpt-5.6-sol','gpt-5.6-luna','gpt-5.4','grok-4.6','deepseek-v4-pro','deepseek-v4-flash','kimi-k2.7-code');

-- Official vendor standard short-context text rates, USD per million tokens.
-- These are customer benchmarks, NOT Azure provider economics.
update public.models m set
 input_price_per_million=p.input_rate, output_price_per_million=p.output_rate,
 cached_input_price_per_million=p.cached_rate, reference_price_source=p.source,
 reference_price_checked_at=now(), reference_price_valid_until='2026-11-21T00:00:00Z',
 pricing_verified=true,
 enabled=p.callable,
 availability_note=case when p.callable then 'Verified standard text inference; configured input/output limits apply' else 'Inference unavailable on the configured resource' end,
 updated_at=now()
from (values
 ('gpt-6-astra',10.00,50.00,1.00,'https://developers.openai.com/api/docs/models/gpt-6-astra',true),
 ('gpt-5.6-sol',4.00,20.00,0.40,'https://developers.openai.com/api/docs/models/gpt-5.6-sol',true),
 ('gpt-5.4',2.50,15.00,0.25,'https://developers.openai.com/api/docs/models/gpt-5.4',true),
 ('gpt-5.6-luna',0.20,1.20,0.02,'https://developers.openai.com/api/docs/pricing',false),
 ('grok-4.6',2.00,6.00,0.50,'https://docs.x.ai/developers/models/grok-4.6',true)
) as p(slug,input_rate,output_rate,cached_rate,source,callable) where m.slug=p.slug;

update public.models set availability_note='Inference responds; reference pricing still requires verification' where slug='deepseek-v4-pro';

-- Retain legacy customer-rate columns only as DB-derived compatibility values.
create function public.sync_customer_model_rates() returns trigger
language plpgsql set search_path='' as $$
begin
  new.customer_input_price_per_million := new.input_price_per_million * (1-new.discount_percent/100);
  new.customer_output_price_per_million := new.output_price_per_million * (1-new.discount_percent/100);
  new.customer_cached_input_price_per_million := coalesce(new.cached_input_price_per_million,new.input_price_per_million) * (1-new.discount_percent/100);
  return new;
end;
$$;
create trigger models_sync_customer_rates before insert or update on public.models
for each row execute function public.sync_customer_model_rates();
update public.models set discount_percent=discount_percent;

alter table public.models
 add constraint models_discount_range check(discount_percent between 0 and 100),
 add constraint models_reference_rates_valid check(input_price_per_million >= 0 and output_price_per_million >= 0 and cached_input_price_per_million >= 0),
 add constraint models_provider_costs_valid check(provider_input_cost_per_million >= 0 and provider_output_cost_per_million >= 0 and provider_cached_input_cost_per_million >= 0),
 add constraint models_pricing_limits_valid check(pricing_max_input_tokens > 0 and pricing_max_output_tokens > 0),
 add constraint models_enabled_requires_pricing check(not enabled or (pricing_verified and reference_price_source is not null and reference_price_checked_at is not null and reference_price_valid_until is not null and input_price_per_million is not null and output_price_per_million is not null));

-- Never expose internal mappings/costs through direct browser table reads.
drop policy if exists models_select_enabled on public.models;
revoke all on public.models from anon,authenticated;
commit;
