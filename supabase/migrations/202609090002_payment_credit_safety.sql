begin;
alter table public.stripe_events enable row level security;
revoke all on public.stripe_events from public,anon,authenticated;

create or replace function public.complete_topup(
 target_stripe_event_id text, target_checkout_session_id text, target_payment_intent_id text,
 target_user_id uuid, target_amount_cents bigint, target_currency text)
returns table(topup_id uuid,wallet_id uuid,balance_after_cents bigint,transaction_id uuid,already_processed boolean)
language plpgsql security definer set search_path = '' as $$
declare w public.wallets; p public.topups; tx public.transactions; claimed uuid;
begin
  if target_stripe_event_id is null or target_stripe_event_id = '' or target_payment_intent_id is null
     or target_amount_cents is null or target_amount_cents not in (1000,2500,5000,10000,50000,100000)
     or target_currency is distinct from 'USD' then raise exception 'invalid_topup'; end if;
  -- Serialize event identity first and then wallet writes in a stable order.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(target_stripe_event_id,0));
  select * into w from public.wallets where user_id = target_user_id for update;
  if w.id is null then raise exception 'wallet_not_found'; end if;
  select * into p from public.topups where stripe_checkout_session_id = target_checkout_session_id for update;
  if p.id is null or p.user_id <> target_user_id or p.amount_cents <> target_amount_cents
     or p.currency <> target_currency
     or (p.stripe_payment_intent_id is not null and p.stripe_payment_intent_id <> target_payment_intent_id) then
     raise exception 'topup_mismatch';
  end if;
  select * into tx from public.transactions where reference_id = 'stripe:' || target_checkout_session_id;
  if p.status in ('COMPLETED','REFUNDED') then
    insert into public.stripe_events(stripe_event_id,event_type) values(target_stripe_event_id,'checkout.session.completed') on conflict(stripe_event_id) do nothing;
    return query select p.id,w.id,tx.balance_after_cents,tx.id,true;
    return;
  end if;
  if p.status <> 'PENDING' or tx.id is not null then raise exception 'invalid_topup_state'; end if;
  if exists(select 1 from public.stripe_events where stripe_event_id = target_stripe_event_id) then raise exception 'event_conflict'; end if;
  update public.wallets set balance_cents = w.balance_cents + p.amount_cents, updated_at = now() where id = w.id;
  insert into public.transactions(user_id,wallet_id,type,amount_cents,balance_after_cents,reference_id,description)
    values(p.user_id,w.id,'TOPUP',p.amount_cents,w.balance_cents+p.amount_cents,'stripe:'||target_checkout_session_id,'Stripe wallet top-up') returning * into tx;
  update public.topups set status='COMPLETED',completed_at=now(),stripe_payment_intent_id=target_payment_intent_id where id=p.id;
  insert into public.stripe_events(stripe_event_id,event_type) values(target_stripe_event_id,'checkout.session.completed');
  return query select p.id,w.id,tx.balance_after_cents,tx.id,false;
end;
$$;
revoke all on function public.complete_topup(text,text,text,uuid,bigint,text) from public,anon,authenticated;
grant execute on function public.complete_topup(text,text,text,uuid,bigint,text) to service_role;
commit;
