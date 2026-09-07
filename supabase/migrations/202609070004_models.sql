create table if not exists public.models (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  display_name text not null,
  provider text not null,
  provider_model_id text not null,
  enabled boolean not null default true,
  input_price_per_million numeric(12,4) not null default 0,
  output_price_per_million numeric(12,4) not null default 0,
  cached_input_price_per_million numeric(12,4),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.models enable row level security;

drop trigger if exists models_set_updated_at on public.models;

create trigger models_set_updated_at
before update on public.models
for each row
execute procedure public.handle_profile_updated_at();

create policy "models_select_enabled"
on public.models
for select
using (enabled = true);

insert into public.models (
  slug,
  display_name,
  provider,
  provider_model_id,
  enabled,
  input_price_per_million,
  output_price_per_million,
  cached_input_price_per_million
)
values
  ('gpt-6-astra', 'GPT-6 Astra', 'azure', 'azure/gpt-6-astra', true, 0, 0, 0),
  ('gpt-5.6-sol', 'GPT-5.6 Sol', 'azure', 'azure/gpt-5.6-sol', true, 0, 0, 0),
  ('gpt-5.6-luna', 'GPT-5.6 Luna', 'azure', 'azure/gpt-5.6-luna', true, 0, 0, 0),
  ('grok-4.6', 'Grok 4.6', 'azure', 'azure/grok-4.6', true, 0, 0, 0),
  ('deepseek-v4-pro', 'DeepSeek V4 Pro', 'azure', 'azure/deepseek-v4-pro', true, 0, 0, 0),
  ('deepseek-v4-flash', 'DeepSeek V4 Flash', 'azure', 'azure/deepseek-v4-flash', true, 0, 0, 0),
  ('kimi-k2.7-code', 'Kimi K2.7 Code', 'azure', 'azure/kimi-k2.7-code', true, 0, 0, 0),
  ('gpt-5.4', 'GPT-5.4', 'azure', 'azure/gpt-5.4', true, 0, 0, 0)
on conflict (slug) do update
set
  display_name = excluded.display_name,
  provider = excluded.provider,
  provider_model_id = excluded.provider_model_id,
  enabled = excluded.enabled,
  input_price_per_million = excluded.input_price_per_million,
  output_price_per_million = excluded.output_price_per_million,
  cached_input_price_per_million = excluded.cached_input_price_per_million,
  updated_at = timezone('utc', now());
