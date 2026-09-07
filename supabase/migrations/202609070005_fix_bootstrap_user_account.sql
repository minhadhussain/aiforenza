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

  select w.id, w.balance_cents
  into current_wallet_id, current_balance
  from public.wallets w
  where w.user_id = target_user_id
  for update;

  grant_reference := 'signup:' || target_user_id::text;

  select exists(
    select 1
    from public.transactions t
    where t.reference_id = grant_reference
  )
  into trial_exists;

  if not trial_exists then
    current_balance := current_balance + 500;

    update public.wallets w
    set balance_cents = current_balance,
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
