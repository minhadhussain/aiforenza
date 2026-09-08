create or replace function public.record_usage_charge(
  target_user_id uuid,
  target_api_key_id uuid,
  target_model_id uuid,
  target_request_id text,
  target_input_tokens integer,
  target_output_tokens integer,
  target_cached_input_tokens integer,
  target_total_tokens integer,
  target_reference_charge_cents bigint,
  target_customer_charge_cents bigint,
  target_customer_savings_cents bigint,
  target_provider_cost_cents bigint,
  target_provider_cost_reference text,
  target_status text
)
returns table (
  wallet_id uuid,
  balance_after_cents bigint,
  transaction_id uuid,
  usage_record_id uuid
)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_wallet_id uuid;
  current_balance bigint;
  new_balance bigint;
  existing_usage_id uuid;
  existing_balance bigint;
  created_transaction_id uuid;
  created_usage_record_id uuid;
begin
  select ur.id
  into existing_usage_id
  from public.usage_records ur
  where ur.request_id = target_request_id;

  if existing_usage_id is not null then
    select ur.id, w.id, w.balance_cents
    into created_usage_record_id, current_wallet_id, existing_balance
    from public.usage_records ur
    join public.wallets w on w.user_id = ur.user_id
    where ur.id = existing_usage_id;

    return query
    select current_wallet_id, existing_balance, null::uuid, created_usage_record_id;
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

  if current_balance < target_customer_charge_cents then
    raise exception 'insufficient_balance';
  end if;

  new_balance := current_balance - target_customer_charge_cents;

  update public.wallets w
  set balance_cents = new_balance,
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
    'USAGE',
    -target_customer_charge_cents,
    new_balance,
    'usage:' || target_request_id,
    'API usage charge'
  )
  returning id into created_transaction_id;

  insert into public.usage_records (
    user_id,
    api_key_id,
    model_id,
    request_id,
    input_tokens,
    output_tokens,
    cached_input_tokens,
    total_tokens,
    reference_charge_cents,
    customer_charge_cents,
    customer_savings_cents,
    provider_cost_cents,
    provider_cost_reference,
    status
  )
  values (
    target_user_id,
    target_api_key_id,
    target_model_id,
    target_request_id,
    target_input_tokens,
    target_output_tokens,
    target_cached_input_tokens,
    target_total_tokens,
    target_reference_charge_cents,
    target_customer_charge_cents,
    target_customer_savings_cents,
    target_provider_cost_cents,
    target_provider_cost_reference,
    target_status
  )
  returning id into created_usage_record_id;

  return query
  select current_wallet_id, new_balance, created_transaction_id, created_usage_record_id;
end;
$$;

grant execute on function public.record_usage_charge(uuid, uuid, uuid, text, integer, integer, integer, integer, bigint, bigint, bigint, bigint, text, text) to service_role;
