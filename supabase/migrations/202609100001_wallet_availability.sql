begin;

-- One database snapshot for both dashboard and preflight reads. The existing
-- reserve_usage RPC still rechecks under a wallet row lock before inference.
create function public.wallet_availability(target_user_id uuid)
returns jsonb language sql stable security definer set search_path = '' as $$
  select to_jsonb(w) || jsonb_build_object(
    'reserved_cents', coalesce(r.held, 0),
    'available_balance_cents', greatest(w.balance_cents - coalesce(r.held, 0), 0)
  )
  from public.wallets w
  left join lateral (
    select sum(amount_cents) as held from public.wallet_reservations
    where user_id = w.user_id
  ) r on true
  where w.user_id = target_user_id;
$$;
revoke all on function public.wallet_availability(uuid) from public, anon, authenticated;
grant execute on function public.wallet_availability(uuid) to service_role;

-- Release only the exact failed request, with an audit trail. No ledger credit:
-- releasing a hold changes spendable capacity, never the cash wallet balance.
create table public.wallet_reservation_releases (
  request_id text primary key,
  user_id uuid not null,
  api_key_id uuid not null,
  model_id uuid not null,
  amount_cents bigint not null,
  reason text not null check(reason in ('provider_rejected', 'provider_not_connected')),
  released_at timestamptz not null default now()
);
alter table public.wallet_reservation_releases enable row level security;
revoke all on public.wallet_reservation_releases from public, anon, authenticated;
grant select on public.wallet_reservation_releases to service_role;

create function public.release_unconsumed_usage(target_request_id text, target_user_id uuid,
  target_api_key_id uuid, target_reason text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare w public.wallets; r public.wallet_reservations; prior public.wallet_reservation_releases;
begin
  if target_reason is null or target_reason not in ('provider_rejected','provider_not_connected') then
    raise exception 'invalid_release_reason';
  end if;
  select * into w from public.wallets where user_id=target_user_id for update;
  if w.id is null then raise exception 'wallet_not_found'; end if;
  select * into prior from public.wallet_reservation_releases where request_id=target_request_id;
  if found then
    if prior.user_id <> target_user_id or prior.api_key_id <> target_api_key_id then
      raise exception 'reservation_owner_mismatch';
    end if;
    return jsonb_build_object('released',true,'already_released',true);
  end if;
  if exists(select 1 from public.usage_records where request_id=target_request_id) then
    return jsonb_build_object('released',false,'already_settled',true);
  end if;
  select * into r from public.wallet_reservations where request_id=target_request_id;
  if not found then return jsonb_build_object('released',false); end if;
  if r.user_id <> target_user_id or r.api_key_id <> target_api_key_id then
    raise exception 'reservation_owner_mismatch';
  end if;
  insert into public.wallet_reservation_releases(request_id,user_id,api_key_id,model_id,amount_cents,reason)
    values(r.request_id,r.user_id,r.api_key_id,r.model_id,r.amount_cents,target_reason);
  delete from public.wallet_reservations where request_id=r.request_id;
  return jsonb_build_object('released',true,'released_cents',r.amount_cents);
end;
$$;
revoke all on function public.release_unconsumed_usage(text,uuid,uuid,text) from public,anon,authenticated;
grant execute on function public.release_unconsumed_usage(text,uuid,uuid,text) to service_role;
commit;
