create table if not exists public.topups (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  stripe_checkout_session_id text not null unique,
  stripe_payment_intent_id text,
  amount_cents bigint not null check (amount_cents > 0),
  currency text not null default 'USD',
  status text not null check (status in ('PENDING', 'COMPLETED', 'FAILED', 'REFUNDED')),
  created_at timestamptz not null default timezone('utc', now()),
  completed_at timestamptz
);

create table if not exists public.stripe_events (
  id uuid primary key default gen_random_uuid(),
  stripe_event_id text not null unique,
  event_type text not null,
  created_at timestamptz not null default timezone('utc', now())
);

alter table public.topups enable row level security;

create policy "topups_select_own"
on public.topups
for select
using (auth.uid() = user_id);

create or replace function public.complete_topup(
  target_stripe_event_id text,
  target_checkout_session_id text,
  target_payment_intent_id text,
  target_user_id uuid,
  target_amount_cents bigint,
  target_currency text
)
returns table (
  topup_id uuid,
  wallet_id uuid,
  balance_after_cents bigint,
  transaction_id uuid,
  already_processed boolean
)
language plpgsql
security definer
set search_path = public
as $$
declare
  existing_event_id uuid;
  current_wallet_id uuid;
  current_balance bigint;
  updated_balance bigint;
  current_topup_id uuid;
  current_topup_status text;
  created_transaction_id uuid;
begin
  select se.id
  into existing_event_id
  from public.stripe_events se
  where se.stripe_event_id = target_stripe_event_id;

  if existing_event_id is not null then
    select t.id, w.id, w.balance_cents
    into current_topup_id, current_wallet_id, current_balance
    from public.topups t
    join public.wallets w on w.user_id = t.user_id
    where t.stripe_checkout_session_id = target_checkout_session_id
    limit 1;

    return query
    select current_topup_id, current_wallet_id, current_balance, null::uuid, true;
    return;
  end if;

  insert into public.stripe_events (stripe_event_id, event_type)
  values (target_stripe_event_id, 'checkout.session.completed');

  insert into public.topups (
    user_id,
    stripe_checkout_session_id,
    stripe_payment_intent_id,
    amount_cents,
    currency,
    status
  )
  values (
    target_user_id,
    target_checkout_session_id,
    target_payment_intent_id,
    target_amount_cents,
    target_currency,
    'PENDING'
  )
  on conflict (stripe_checkout_session_id) do update
    set stripe_payment_intent_id = coalesce(excluded.stripe_payment_intent_id, public.topups.stripe_payment_intent_id)
  returning id, status into current_topup_id, current_topup_status;

  if current_topup_status = 'COMPLETED' then
    select w.id, w.balance_cents
    into current_wallet_id, current_balance
    from public.wallets w
    where w.user_id = target_user_id;

    return query
    select current_topup_id, current_wallet_id, current_balance, null::uuid, false;
    return;
  end if;

  select w.id, w.balance_cents
  into current_wallet_id, current_balance
  from public.wallets w
  where w.user_id = target_user_id
  for update;

  if current_wallet_id is null then
    raise exception 'wallet_not_found';
  end if;

  updated_balance := current_balance + target_amount_cents;

  update public.wallets w
  set balance_cents = updated_balance,
      updated_at = timezone('utc', now())
  where w.id = current_wallet_id;

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
    'TOPUP',
    target_amount_cents,
    updated_balance,
    'stripe:' || target_checkout_session_id,
    'Stripe wallet top-up'
  )
  returning id into created_transaction_id;

  update public.topups t
  set status = 'COMPLETED',
      completed_at = timezone('utc', now())
  where t.id = current_topup_id;

  return query
  select current_topup_id, current_wallet_id, updated_balance, created_transaction_id, false;
end;
$$;

grant execute on function public.complete_topup(text, text, text, uuid, bigint, text) to service_role;
