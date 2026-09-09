-- Forward-only migration. Existing financial history is not rewritten.
begin;
create table public.wallet_reservations (
  request_id text primary key,
  user_id uuid not null references public.profiles(id),
  api_key_id uuid not null references public.api_keys(id),
  model_id uuid not null references public.models(id),
  amount_cents bigint not null check (amount_cents >= 0),
  created_at timestamptz not null default now()
);
alter table public.wallet_reservations enable row level security;
revoke all on public.wallet_reservations from public, anon, authenticated;
grant select on public.wallet_reservations to service_role;

create function public.reserve_usage(target_request_id text, target_user_id uuid,
  target_api_key_id uuid, target_model_id uuid, target_amount_cents bigint)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare w public.wallets; r public.wallet_reservations; held bigint;
begin
  if target_amount_cents is null or target_amount_cents < 0 then raise exception 'invalid_amount'; end if;
  select * into w from public.wallets where user_id = target_user_id for update;
  if w.id is null then raise exception 'wallet_not_found'; end if;
  if not exists(select 1 from public.api_keys where id = target_api_key_id and user_id = target_user_id and revoked_at is null)
     or not exists(select 1 from public.models where id = target_model_id and enabled) then raise exception 'access_denied'; end if;
  select * into r from public.wallet_reservations where request_id = target_request_id;
  if found then
    if r.user_id <> target_user_id or r.api_key_id <> target_api_key_id or r.model_id <> target_model_id or r.amount_cents <> target_amount_cents then
      raise exception 'request_conflict';
    end if;
    return jsonb_build_object('reserved', true);
  end if;
  if exists(select 1 from public.usage_records where request_id = target_request_id) then raise exception 'request_already_billed'; end if;
  select coalesce(sum(amount_cents),0) into held from public.wallet_reservations where user_id = target_user_id;
  if w.balance_cents <= 0 or w.balance_cents - held < target_amount_cents then raise exception 'insufficient_balance'; end if;
  insert into public.wallet_reservations values(target_request_id,target_user_id,target_api_key_id,target_model_id,target_amount_cents,now());
  return jsonb_build_object('reserved',true,'available_cents',w.balance_cents-held-target_amount_cents);
end;
$$;

-- Preserve the existing atomic ledger writer but remove direct API access to it.
alter function public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,integer,bigint,bigint,bigint,bigint,text,text)
  rename to record_usage_charge_unreserved;
revoke all on function public.record_usage_charge_unreserved(uuid,uuid,uuid,text,integer,integer,integer,integer,bigint,bigint,bigint,bigint,text,text) from public,anon,authenticated,service_role;
revoke all on function public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,bigint,text,text) from public,anon,authenticated,service_role;

create function public.record_usage_charge(
 target_user_id uuid, target_api_key_id uuid, target_model_id uuid, target_request_id text,
 target_input_tokens integer,target_output_tokens integer,target_cached_input_tokens integer,target_total_tokens integer,
 target_reference_charge_cents bigint,target_customer_charge_cents bigint,target_customer_savings_cents bigint,
 target_provider_cost_cents bigint,target_provider_cost_reference text,target_status text)
returns table(wallet_id uuid,balance_after_cents bigint,transaction_id uuid,usage_record_id uuid)
language plpgsql security definer set search_path = '' as $$
declare w public.wallets; r public.wallet_reservations; u public.usage_records; t public.transactions;
begin
  if target_customer_charge_cents is null or target_customer_charge_cents < 0
     or target_reference_charge_cents is null or target_customer_savings_cents is null
     or target_reference_charge_cents < target_customer_charge_cents
     or target_customer_savings_cents <> target_reference_charge_cents-target_customer_charge_cents
     or target_input_tokens is null or target_output_tokens is null or target_cached_input_tokens is null
     or target_input_tokens < 0 or target_output_tokens < 0 or target_cached_input_tokens < 0
     or target_cached_input_tokens > target_input_tokens
     or target_total_tokens is null or target_total_tokens <> target_input_tokens+target_output_tokens
     or target_status is distinct from 'completed'
     or target_provider_cost_cents < 0 then raise exception 'invalid_billing'; end if;
  select * into w from public.wallets where user_id = target_user_id for update;
  if w.id is null then raise exception 'wallet_not_found'; end if;
  select * into u from public.usage_records where request_id = target_request_id;
  if found then
    if u.user_id <> target_user_id or u.api_key_id <> target_api_key_id or u.model_id <> target_model_id
       or u.customer_charge_cents <> target_customer_charge_cents or u.input_tokens <> target_input_tokens
       or u.output_tokens <> target_output_tokens or u.cached_input_tokens <> target_cached_input_tokens
       or u.reference_charge_cents is distinct from target_reference_charge_cents then raise exception 'request_conflict'; end if;
    select * into t from public.transactions where reference_id = 'usage:' || target_request_id;
    return query select w.id,t.balance_after_cents,t.id,u.id;
    return;
  end if;
  select * into r from public.wallet_reservations where request_id = target_request_id;
  if r.request_id is null or r.user_id <> target_user_id or r.api_key_id <> target_api_key_id or r.model_id <> target_model_id then
    raise exception 'reservation_missing';
  end if;
  if target_customer_charge_cents > r.amount_cents then raise exception 'reservation_exceeded'; end if;
  return query select * from public.record_usage_charge_unreserved(target_user_id,target_api_key_id,target_model_id,target_request_id,
    target_input_tokens,target_output_tokens,target_cached_input_tokens,target_total_tokens,target_reference_charge_cents,
    target_customer_charge_cents,target_customer_savings_cents,target_provider_cost_cents,target_provider_cost_reference,target_status);
  delete from public.wallet_reservations where request_id = target_request_id;
end;
$$;
revoke all on function public.reserve_usage(text,uuid,uuid,uuid,bigint) from public,anon,authenticated;
grant execute on function public.reserve_usage(text,uuid,uuid,uuid,bigint) to service_role;
revoke all on function public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,integer,bigint,bigint,bigint,bigint,text,text) from public,anon,authenticated;
grant execute on function public.record_usage_charge(uuid,uuid,uuid,text,integer,integer,integer,integer,bigint,bigint,bigint,bigint,text,text) to service_role;
-- These existing privileged RPCs must not be callable by browser roles.
revoke all on function public.bootstrap_user_account(uuid,text) from public,anon,authenticated;
revoke all on function public.complete_topup(text,text,text,uuid,bigint,text) from public,anon,authenticated;
commit;
