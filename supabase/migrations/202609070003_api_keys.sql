create table if not exists public.api_keys (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  name text not null,
  key_prefix text not null,
  key_hash text not null,
  last_used_at timestamptz,
  created_at timestamptz not null default timezone('utc', now()),
  revoked_at timestamptz
);

create unique index if not exists api_keys_key_hash_idx on public.api_keys (key_hash);
create index if not exists api_keys_user_id_idx on public.api_keys (user_id);

alter table public.api_keys enable row level security;

create policy "api_keys_select_own"
on public.api_keys
for select
using (auth.uid() = user_id);
