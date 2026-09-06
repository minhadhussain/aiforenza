create extension if not exists pgcrypto;

create table if not exists public.wallets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references public.profiles (id) on delete cascade,
  balance_cents bigint not null default 0 check (balance_cents >= 0),
  currency text not null default 'USD',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.transactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  wallet_id uuid not null references public.wallets (id) on delete cascade,
  type text not null check (type in ('FREE_TRIAL', 'TOPUP', 'USAGE', 'REFUND', 'ADJUSTMENT')),
  amount_cents bigint not null,
  balance_after_cents bigint not null check (balance_after_cents >= 0),
  reference_id text unique,
  description text not null,
  created_at timestamptz not null default timezone('utc', now())
);

alter table public.wallets enable row level security;
alter table public.transactions enable row level security;

drop trigger if exists wallets_set_updated_at on public.wallets;

create trigger wallets_set_updated_at
before update on public.wallets
for each row
execute procedure public.handle_profile_updated_at();

create policy "wallets_select_own"
on public.wallets
for select
using (auth.uid() = user_id);

create policy "transactions_select_own"
on public.transactions
for select
using (auth.uid() = user_id);

create or replace function public.bootstrap_user_account(target_user_id uuid, target_email text)
returns table (
  wallet_id uuid,
  balance_cents bigint,
  currency text,
  trial_granted boolean
)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_wallet_id uuid;
  current_balance bigint;
  grant_reference text;
  trial_exists boolean;
begin
  insert into public.profiles (id, email)
  values (target_user_id, target_email)
  on conflict (id) do update
    set email = excluded.email,
        updated_at = timezone('utc', now());

  insert into public.wallets (user_id)
  values (target_user_id)
  on conflict (user_id) do nothing;

  select id, balance_cents
  into current_wallet_id, current_balance
  from public.wallets
  where user_id = target_user_id
  for update;

  grant_reference := 'signup:' || target_user_id::text;

  select exists(
    select 1
    from public.transactions
    where reference_id = grant_reference
  )
  into trial_exists;

  if not trial_exists then
    current_balance := current_balance + 500;

    update public.wallets
    set balance_cents = current_balance,
        updated_at = timezone('utc', now())
    where id = current_wallet_id;

    insert into public.transactions (
      user_id,
      wallet_id,
      type,
      amount_cents,
      balance_after_cents,
      reference_id,
      description
    )
    values (
      target_user_id,
      current_wallet_id,
      'FREE_TRIAL',
      500,
      current_balance,
      grant_reference,
      'Initial $5.00 trial credit'
    );
  end if;

  return query
  select
    w.id,
    w.balance_cents,
    w.currency,
    not trial_exists
  from public.wallets w
  where w.id = current_wallet_id;
end;
$$;

grant execute on function public.bootstrap_user_account(uuid, text) to service_role;
