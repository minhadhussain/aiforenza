begin;

create table public.hackathon_campaigns (
 id uuid primary key default gen_random_uuid(), name text not null unique,
 grant_amount_cents bigint not null default 10000 check(grant_amount_cents=10000),
 status text not null default 'INACTIVE' check(status in ('ACTIVE','INACTIVE')),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now()
);
-- The claim endpoint does not trust a client-supplied campaign; exactly one may be active.
create unique index hackathon_one_active_campaign on public.hackathon_campaigns((status)) where status='ACTIVE';
create table public.hackathon_team_grants (
 id uuid primary key default gen_random_uuid(), campaign_id uuid not null references public.hackathon_campaigns(id),
 team_id text not null check(team_id ~ '^[A-Z0-9][A-Z0-9_-]{2,63}$'),
 claimed_by_user_id uuid references public.profiles(id), claimed_at timestamptz,
 wallet_id uuid unique, api_key_id uuid unique,
 status text not null default 'UNCLAIMED' check(status in ('UNCLAIMED','ACTIVE','DISABLED')),
 created_at timestamptz not null default now(), updated_at timestamptz not null default now(),
 unique(campaign_id,team_id),
 check((status='UNCLAIMED' and claimed_by_user_id is null and claimed_at is null and wallet_id is null and api_key_id is null)
    or (status in ('ACTIVE','DISABLED') and claimed_by_user_id is not null and claimed_at is not null and wallet_id is not null and api_key_id is not null))
);
alter table public.wallets alter column user_id drop not null;
alter table public.wallets add column billing_source text not null default 'PAID' check(billing_source in ('PAID','PROMOTIONAL'));
alter table public.wallets add column hackathon_grant_id uuid unique references public.hackathon_team_grants(id);
alter table public.wallets add constraint wallet_billing_owner check(
 (billing_source='PAID' and user_id is not null and hackathon_grant_id is null) or
 (billing_source='PROMOTIONAL' and user_id is null and hackathon_grant_id is not null));
alter table public.wallets add constraint wallet_id_grant_unique unique(id,hackathon_grant_id);
alter table public.api_keys add column billing_source text not null default 'PAID' check(billing_source in ('PAID','PROMOTIONAL'));
alter table public.api_keys add column hackathon_grant_id uuid unique references public.hackathon_team_grants(id);
alter table public.api_keys add constraint key_billing_owner check(
 (billing_source='PAID' and hackathon_grant_id is null) or (billing_source='PROMOTIONAL' and hackathon_grant_id is not null));
alter table public.api_keys add constraint key_id_grant_unique unique(id,hackathon_grant_id);
alter table public.hackathon_team_grants add constraint grant_wallet_fk foreign key(wallet_id,id) references public.wallets(id,hackathon_grant_id) deferrable initially deferred;
alter table public.hackathon_team_grants add constraint grant_key_fk foreign key(api_key_id,id) references public.api_keys(id,hackathon_grant_id) deferrable initially deferred;

alter table public.transactions drop constraint transactions_type_check;
alter table public.transactions add constraint transactions_type_check check(type in ('FREE_TRIAL','TOPUP','USAGE','REFUND','ADJUSTMENT','PROMO_GRANT'));
-- One shared ledger/reservation system, with explicit immutable attribution.
do $$ declare t text; begin
 foreach t in array array['transactions','usage_records','wallet_reservations','wallet_reservation_releases','request_rejections'] loop
  execute format('alter table public.%I add column billing_source text not null default ''PAID'' check(billing_source in (''PAID'',''PROMOTIONAL''))',t);
  execute format('alter table public.%I add column hackathon_grant_id uuid references public.hackathon_team_grants(id)',t);
  execute format('alter table public.%I add constraint %I check ((billing_source=''PAID'' and hackathon_grant_id is null) or (billing_source=''PROMOTIONAL'' and hackathon_grant_id is not null))',t,t||'_billing_scope');
 end loop;
end $$;
create unique index promo_grant_credit_once on public.transactions(hackathon_grant_id) where type='PROMO_GRANT';
alter table public.transactions add constraint promotional_grant_amount check(type<>'PROMO_GRANT' or (billing_source='PROMOTIONAL' and amount_cents=10000 and balance_after_cents=10000));
alter table public.usage_records add constraint promotional_reference_charge check(billing_source<>'PROMOTIONAL' or (customer_charge_cents=reference_charge_cents and customer_savings_cents=0));
-- Keep the original hold's provenance after the active reservation is consumed.
-- Historical rows are untouched; new rows are stamped by the existing ledger writer.
alter table public.usage_records add column reserved_amount_cents bigint check(reserved_amount_cents>=0);
alter table public.usage_records add column reservation_created_at timestamptz;
alter table public.usage_records add constraint promotional_reservation_audit check(
 billing_source<>'PROMOTIONAL' or (reserved_amount_cents is not null and reservation_created_at is not null
 and reserved_amount_cents>=customer_charge_cents));
create index hackathon_claimant on public.hackathon_team_grants(claimed_by_user_id) where claimed_by_user_id is not null;
create index promotional_holds on public.wallet_reservations(hackathon_grant_id) where hackathon_grant_id is not null;

-- No browser role can preload IDs, issue grants, redirect keys, or mutate money.
alter table public.hackathon_campaigns enable row level security;
alter table public.hackathon_team_grants enable row level security;
revoke all on public.hackathon_campaigns,public.hackathon_team_grants from public,anon,authenticated;
grant select on public.hackathon_campaigns,public.hackathon_team_grants to service_role;

create function public.hackathon_scope_immutable() returns trigger language plpgsql set search_path='' as $$
begin
 if tg_table_name in ('wallets','api_keys') then
  if new.billing_source is distinct from old.billing_source or new.hackathon_grant_id is distinct from old.hackathon_grant_id
     or new.user_id is distinct from old.user_id then raise exception 'billing_scope_immutable'; end if;
 else
  if old.status<>'UNCLAIMED' and (new.status='UNCLAIMED' or new.campaign_id<>old.campaign_id or new.team_id<>old.team_id
     or new.claimed_by_user_id is distinct from old.claimed_by_user_id or new.claimed_at is distinct from old.claimed_at
     or new.wallet_id is distinct from old.wallet_id or new.api_key_id is distinct from old.api_key_id) then raise exception 'claim_immutable'; end if;
 end if;
 return new;
end $$;
create trigger wallet_scope_immutable before update on public.wallets for each row execute function public.hackathon_scope_immutable();
create trigger key_scope_immutable before update on public.api_keys for each row execute function public.hackathon_scope_immutable();
create trigger claim_scope_immutable before update on public.hackathon_team_grants for each row execute function public.hackathon_scope_immutable();

create function public.check_claim_integrity() returns trigger language plpgsql security definer set search_path='' as $$
declare g public.hackathon_team_grants;
begin
 select * into g from public.hackathon_team_grants where id=new.id;
 if g.status<>'UNCLAIMED' and (
  not exists(select 1 from public.wallets where id=g.wallet_id and hackathon_grant_id=g.id and billing_source='PROMOTIONAL' and user_id is null)
  or not exists(select 1 from public.api_keys where id=g.api_key_id and hackathon_grant_id=g.id and user_id=g.claimed_by_user_id and billing_source='PROMOTIONAL')
  or not exists(select 1 from public.transactions where hackathon_grant_id=g.id and wallet_id=g.wallet_id and user_id=g.claimed_by_user_id and type='PROMO_GRANT' and amount_cents=10000)
 ) then raise exception 'claim_integrity_violation'; end if;
 return null;
end $$;
create constraint trigger claim_integrity after insert or update on public.hackathon_team_grants deferrable initially deferred for each row execute function public.check_claim_integrity();
-- The reverse direction also matters: no orphan promotional wallet/key can be
-- inserted against an unclaimed Team ID, even by an accidental privileged write.
create function public.check_promotional_owner() returns trigger language plpgsql security definer set search_path='' as $$
declare g public.hackathon_team_grants;
begin
 if new.billing_source='PROMOTIONAL' then
  select * into g from public.hackathon_team_grants where id=new.hackathon_grant_id;
  if g.id is null or g.status='UNCLAIMED' then raise exception 'claim_integrity_violation'; end if;
  if tg_table_name='wallets' and g.wallet_id<>new.id then raise exception 'claim_integrity_violation'; end if;
  if tg_table_name='api_keys' and (g.api_key_id<>new.id or g.claimed_by_user_id<>new.user_id) then raise exception 'claim_integrity_violation'; end if;
 end if;
 return null;
end $$;
create constraint trigger promotional_wallet_owner after insert on public.wallets deferrable initially deferred for each row execute function public.check_promotional_owner();
create constraint trigger promotional_key_owner after insert on public.api_keys deferrable initially deferred for each row execute function public.check_promotional_owner();
create function public.promo_history_immutable() returns trigger language plpgsql set search_path='' as $$
begin
 if old.billing_source='PROMOTIONAL' then
  if tg_table_name='api_keys' and tg_op='UPDATE' then
   if new.key_hash is distinct from old.key_hash or new.key_prefix is distinct from old.key_prefix then raise exception 'promotional_key_immutable'; end if;
   return new;
  end if;
  raise exception 'promotional_history_immutable';
 end if;
 if tg_op='DELETE' then return old; end if;
 return new;
end $$;
create trigger promo_ledger_immutable before update or delete on public.transactions for each row execute function public.promo_history_immutable();
create trigger promo_usage_immutable before update or delete on public.usage_records for each row execute function public.promo_history_immutable();
create trigger promo_key_material_immutable before update or delete on public.api_keys for each row execute function public.promo_history_immutable();

create function public.resolve_key_wallet(target_user_id uuid,target_api_key_id uuid, require_active boolean default true)
returns uuid language plpgsql security definer set search_path='' as $$
declare k public.api_keys; g public.hackathon_team_grants; wid uuid;
begin
 select * into k from public.api_keys where id=target_api_key_id and user_id=target_user_id;
 if k.id is null or (require_active and k.revoked_at is not null) then raise exception 'access_denied'; end if;
 if k.billing_source='PROMOTIONAL' then
  select * into g from public.hackathon_team_grants where id=k.hackathon_grant_id;
  if g.api_key_id is distinct from k.id or g.claimed_by_user_id is distinct from k.user_id
    or (require_active and g.status<>'ACTIVE') then raise exception 'access_denied'; end if;
  select id into wid from public.wallets where id=g.wallet_id and hackathon_grant_id=g.id and billing_source='PROMOTIONAL' and user_id is null;
 else
  select id into wid from public.wallets where user_id=target_user_id and billing_source='PAID';
 end if;
 if wid is null then raise exception 'wallet_not_found'; end if;
 return wid;
end $$;
revoke all on function public.resolve_key_wallet(uuid,uuid,boolean) from public,anon,authenticated,service_role;

-- Stamp all new activity from the key/wallet, not request input, including legacy paid writers.
create function public.stamp_billing_scope() returns trigger language plpgsql security definer set search_path='' as $$
declare w public.wallets; k public.api_keys; g public.hackathon_team_grants;
begin
 if tg_table_name='transactions' then
  select * into w from public.wallets where id=new.wallet_id;
  if w.billing_source='PROMOTIONAL' then
   select * into g from public.hackathon_team_grants where id=w.hackathon_grant_id;
   if g.claimed_by_user_id is distinct from new.user_id or new.type not in ('PROMO_GRANT','USAGE') then raise exception 'promotional_ledger_mismatch'; end if;
  elsif w.user_id is distinct from new.user_id then raise exception 'wallet_owner_mismatch'; end if;
  new.billing_source:=w.billing_source; new.hackathon_grant_id:=w.hackathon_grant_id;
 else
  select * into k from public.api_keys where id=new.api_key_id and user_id=new.user_id;
  if k.id is null then raise exception 'access_denied'; end if;
  new.billing_source:=k.billing_source; new.hackathon_grant_id:=k.hackathon_grant_id;
  if tg_table_name='usage_records' then
   select amount_cents,created_at into new.reserved_amount_cents,new.reservation_created_at
   from public.wallet_reservations where request_id=new.request_id and api_key_id=new.api_key_id and user_id=new.user_id;
  end if;
 end if;
 return new;
end $$;
do $$ declare t text; begin
 foreach t in array array['transactions','usage_records','wallet_reservations','wallet_reservation_releases','request_rejections'] loop
  execute format('create trigger stamp_billing_scope before insert on public.%I for each row execute function public.stamp_billing_scope()',t);
 end loop;
end $$;

create function public.claim_hackathon_team(target_user_id uuid,target_team_id text,target_key_hash text,target_key_prefix text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare c public.hackathon_campaigns; g public.hackathon_team_grants; wid uuid; kid uuid;
begin
 if target_key_hash !~ '^[a-f0-9]{64}$' or target_key_hash is null or target_key_prefix is null or length(target_key_prefix)>24 then raise exception 'invalid_key'; end if;
 if not exists(select 1 from public.profiles where id=target_user_id) then raise exception 'user_not_found'; end if;
 select * into c from public.hackathon_campaigns where status='ACTIVE' for share;
 if c.id is null then raise exception 'campaign_inactive'; end if;
 select * into g from public.hackathon_team_grants where campaign_id=c.id and team_id=target_team_id for update;
 if g.id is null then raise exception 'invalid_team_id'; end if;
 if g.status<>'UNCLAIMED' then raise exception 'team_already_claimed'; end if;
 wid:=gen_random_uuid(); kid:=gen_random_uuid();
 update public.hackathon_team_grants set claimed_by_user_id=target_user_id,claimed_at=now(),wallet_id=wid,api_key_id=kid,status='ACTIVE',updated_at=now() where id=g.id;
 insert into public.wallets(id,user_id,balance_cents,currency,billing_source,hackathon_grant_id)
   values(wid,null,10000,'USD','PROMOTIONAL',g.id);
 insert into public.api_keys(id,user_id,name,key_prefix,key_hash,billing_source,hackathon_grant_id)
   values(kid,target_user_id,'Hackathon '||g.team_id,target_key_prefix,target_key_hash,'PROMOTIONAL',g.id);
 insert into public.transactions(user_id,wallet_id,type,amount_cents,balance_after_cents,reference_id,description)
   values(target_user_id,wid,'PROMO_GRANT',10000,10000,'hackathon:'||g.id,'Hackathon $100 promotional grant');
 return jsonb_build_object('team_id',g.team_id,'campaign_name',c.name,'status','ACTIVE','promo_balance_cents',10000,'reserved_cents',0,'available_balance_cents',10000,'billing_source','PROMOTIONAL');
end $$;
revoke all on function public.claim_hackathon_team(uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.claim_hackathon_team(uuid,text,text,text) to service_role;

create function public.hackathon_status(target_user_id uuid) returns jsonb language sql stable security definer set search_path='' as $$
 select jsonb_build_object('campaign',(select jsonb_build_object('name',name,'grant_amount_cents',grant_amount_cents) from public.hackathon_campaigns where status='ACTIVE'),
 'grants',coalesce((select jsonb_agg(jsonb_build_object('team_id',g.team_id,'campaign_name',c.name,'status',g.status,
 'promo_balance_cents',w.balance_cents,'reserved_cents',coalesce(r.held,0),'available_balance_cents',greatest(w.balance_cents-coalesce(r.held,0),0),
 'claimed_at',g.claimed_at,'key_revoked',k.revoked_at is not null,'billing_source','PROMOTIONAL') order by g.claimed_at desc)
 from public.hackathon_team_grants g join public.hackathon_campaigns c on c.id=g.campaign_id
 join public.wallets w on w.id=g.wallet_id join public.api_keys k on k.id=g.api_key_id
 left join lateral(select sum(amount_cents) held from public.wallet_reservations where hackathon_grant_id=g.id) r on true
 where g.claimed_by_user_id=target_user_id),'[]'::jsonb));
$$;
revoke all on function public.hackathon_status(uuid) from public,anon,authenticated;
grant execute on function public.hackathon_status(uuid) to service_role;

create or replace function public.wallet_availability(target_user_id uuid)
returns jsonb language sql stable security definer set search_path='' as $$
 select to_jsonb(w)||jsonb_build_object('reserved_cents',coalesce(r.held,0),'available_balance_cents',greatest(w.balance_cents-coalesce(r.held,0),0))
 from public.wallets w left join lateral(select sum(amount_cents) held from public.wallet_reservations where user_id=w.user_id and billing_source='PAID') r on true
 where w.user_id=target_user_id and w.billing_source='PAID';
$$;
create function public.api_key_wallet(target_user_id uuid,target_api_key_id uuid)
returns jsonb language sql stable security definer set search_path='' as $$
 select to_jsonb(w)||jsonb_build_object('reserved_cents',coalesce(r.held,0),'available_balance_cents',greatest(w.balance_cents-coalesce(r.held,0),0))
 from public.wallets w left join lateral(select sum(amount_cents) held from public.wallet_reservations r
 where (w.billing_source='PAID' and r.billing_source='PAID' and r.user_id=w.user_id)
 or (w.billing_source='PROMOTIONAL' and r.hackathon_grant_id=w.hackathon_grant_id)) r on true
 where w.id=public.resolve_key_wallet(target_user_id,target_api_key_id,true);
$$;
revoke all on function public.api_key_wallet(uuid,uuid) from public,anon,authenticated;
grant execute on function public.api_key_wallet(uuid,uuid) to service_role;

create or replace function public.reserve_usage(target_request_id text,target_user_id uuid,target_api_key_id uuid,target_model_id uuid,target_amount_cents bigint)
returns jsonb language plpgsql security definer set search_path='' as $$
declare w public.wallets; r public.wallet_reservations; held bigint; wid uuid;
begin
 if target_amount_cents is null or target_amount_cents<0 then raise exception 'invalid_amount'; end if;
 wid:=public.resolve_key_wallet(target_user_id,target_api_key_id,true);
 select * into w from public.wallets where id=wid for update;
 if not exists(select 1 from public.models where id=target_model_id and enabled) then raise exception 'access_denied'; end if;
 select * into r from public.wallet_reservations where request_id=target_request_id;
 if found then
  if r.user_id<>target_user_id or r.api_key_id<>target_api_key_id or r.model_id<>target_model_id or r.amount_cents<>target_amount_cents then raise exception 'request_conflict'; end if;
  return jsonb_build_object('reserved',true);
 end if;
 if exists(select 1 from public.usage_records where request_id=target_request_id) or exists(select 1 from public.wallet_reservation_releases where request_id=target_request_id) then raise exception 'request_already_billed'; end if;
 select coalesce(sum(amount_cents),0) into held from public.wallet_reservations where
   (w.billing_source='PAID' and billing_source='PAID' and user_id=target_user_id) or
   (w.billing_source='PROMOTIONAL' and hackathon_grant_id=w.hackathon_grant_id);
 if w.balance_cents<=0 or w.balance_cents-held<target_amount_cents then raise exception 'insufficient_balance'; end if;
 insert into public.wallet_reservations(request_id,user_id,api_key_id,model_id,amount_cents) values(target_request_id,target_user_id,target_api_key_id,target_model_id,target_amount_cents);
 return jsonb_build_object('reserved',true,'available_cents',w.balance_cents-held-target_amount_cents);
end $$;

create or replace function public.record_usage_charge(target_user_id uuid,target_api_key_id uuid,target_model_id uuid,target_request_id text,
 target_input_tokens integer,target_output_tokens integer,target_cached_input_tokens integer,target_total_tokens integer,
 target_reference_charge_cents bigint,target_customer_charge_cents bigint,target_customer_savings_cents bigint,
 target_provider_cost_cents bigint,target_provider_cost_reference text,target_status text)
returns table(wallet_id uuid,balance_after_cents bigint,transaction_id uuid,usage_record_id uuid)
language plpgsql security definer set search_path='' as $$
declare w public.wallets; r public.wallet_reservations; u public.usage_records; t public.transactions; wid uuid; new_balance bigint;
begin
 if target_customer_charge_cents is null or target_customer_charge_cents<0 or target_reference_charge_cents is null
 or target_customer_savings_cents is null or target_reference_charge_cents<target_customer_charge_cents
 or target_customer_savings_cents<>target_reference_charge_cents-target_customer_charge_cents
 or target_input_tokens is null or target_output_tokens is null or target_cached_input_tokens is null
 or target_input_tokens<0 or target_output_tokens<0 or target_cached_input_tokens<0 or target_cached_input_tokens>target_input_tokens
 or target_total_tokens is null or target_total_tokens<>target_input_tokens+target_output_tokens
 or target_status is distinct from 'completed' or target_provider_cost_cents<0 then raise exception 'invalid_billing'; end if;
 -- Revoked/disabled keys must still settle inference already reserved before revocation.
 wid:=public.resolve_key_wallet(target_user_id,target_api_key_id,false);
 select * into w from public.wallets where id=wid for update;
 if w.billing_source='PROMOTIONAL' and (target_customer_charge_cents<>target_reference_charge_cents or target_customer_savings_cents<>0) then raise exception 'promotional_discount_forbidden'; end if;
 select * into u from public.usage_records where request_id=target_request_id;
 if found then
  if u.user_id<>target_user_id or u.api_key_id<>target_api_key_id or u.model_id<>target_model_id
   or u.customer_charge_cents<>target_customer_charge_cents or u.input_tokens<>target_input_tokens or u.output_tokens<>target_output_tokens
   or u.cached_input_tokens<>target_cached_input_tokens or u.reference_charge_cents is distinct from target_reference_charge_cents then raise exception 'request_conflict'; end if;
  select * into t from public.transactions where reference_id='usage:'||target_request_id;
  return query select w.id,t.balance_after_cents,t.id,u.id; return;
 end if;
 select * into r from public.wallet_reservations where request_id=target_request_id;
 if r.request_id is null or r.user_id<>target_user_id or r.api_key_id<>target_api_key_id or r.model_id<>target_model_id
  or r.hackathon_grant_id is distinct from w.hackathon_grant_id then raise exception 'reservation_missing'; end if;
 if target_customer_charge_cents>r.amount_cents then raise exception 'reservation_exceeded'; end if;
 if w.balance_cents<target_customer_charge_cents then raise exception 'insufficient_balance'; end if;
 new_balance:=w.balance_cents-target_customer_charge_cents;
 update public.wallets set balance_cents=new_balance,updated_at=now() where id=w.id;
 insert into public.transactions(user_id,wallet_id,type,amount_cents,balance_after_cents,reference_id,description)
 values(target_user_id,w.id,'USAGE',-target_customer_charge_cents,new_balance,'usage:'||target_request_id,'API usage charge') returning * into t;
 insert into public.usage_records(user_id,api_key_id,model_id,request_id,input_tokens,output_tokens,cached_input_tokens,total_tokens,
  reference_charge_cents,customer_charge_cents,customer_savings_cents,provider_cost_cents,provider_cost_reference,status)
 values(target_user_id,target_api_key_id,target_model_id,target_request_id,target_input_tokens,target_output_tokens,target_cached_input_tokens,target_total_tokens,
  target_reference_charge_cents,target_customer_charge_cents,target_customer_savings_cents,target_provider_cost_cents,target_provider_cost_reference,target_status) returning * into u;
 delete from public.wallet_reservations where request_id=target_request_id;
 return query select w.id,new_balance,t.id,u.id;
end $$;

create or replace function public.release_unconsumed_usage(target_request_id text,target_user_id uuid,target_api_key_id uuid,target_reason text)
returns jsonb language plpgsql security definer set search_path='' as $$
declare w public.wallets; r public.wallet_reservations; prior public.wallet_reservation_releases; wid uuid;
begin
 if target_reason is null or target_reason not in ('provider_rejected','provider_not_connected') then raise exception 'invalid_release_reason'; end if;
 wid:=public.resolve_key_wallet(target_user_id,target_api_key_id,false);
 select * into w from public.wallets where id=wid for update;
 select * into prior from public.wallet_reservation_releases where request_id=target_request_id;
 if found then
  if prior.user_id<>target_user_id or prior.api_key_id<>target_api_key_id then raise exception 'reservation_owner_mismatch'; end if;
  return jsonb_build_object('released',true,'already_released',true);
 end if;
 if exists(select 1 from public.usage_records where request_id=target_request_id) then return jsonb_build_object('released',false,'already_settled',true); end if;
 select * into r from public.wallet_reservations where request_id=target_request_id;
 if not found then return jsonb_build_object('released',false); end if;
 if r.user_id<>target_user_id or r.api_key_id<>target_api_key_id then raise exception 'reservation_owner_mismatch'; end if;
 insert into public.wallet_reservation_releases(request_id,user_id,api_key_id,model_id,amount_cents,reason) values(r.request_id,r.user_id,r.api_key_id,r.model_id,r.amount_cents,target_reason);
 delete from public.wallet_reservations where request_id=target_request_id;
 return jsonb_build_object('released',true,'released_cents',r.amount_cents);
end $$;

-- Existing activity remains account scoped and gains source labels without rewriting history.
alter function public.dashboard_activity(uuid,integer,integer,text,uuid,text,timestamptz) rename to dashboard_activity_base;
revoke all on function public.dashboard_activity_base(uuid,integer,integer,text,uuid,text,timestamptz) from public,anon,authenticated,service_role;
create function public.dashboard_activity(target_user_id uuid,page_size integer default 25,page_number integer default 1,
 filter_model text default null,filter_key uuid default null,filter_status text default null,snapshot_at timestamptz default now())
returns jsonb language sql stable security definer set search_path='' as $$
 with base as (select public.dashboard_activity_base(target_user_id,page_size,page_number,filter_model,filter_key,filter_status,snapshot_at) payload)
 select payload||jsonb_build_object('data',coalesce((select jsonb_agg(item||jsonb_build_object('billing_source',k.billing_source,'hackathon_team_id',g.team_id,'hackathon_campaign',c.name) order by ordinal)
 from jsonb_array_elements(payload->'data') with ordinality a(item,ordinal)
 join public.api_keys k on k.id=(item->>'api_key_id')::uuid and k.user_id=target_user_id
 left join public.hackathon_team_grants g on g.id=k.hackathon_grant_id left join public.hackathon_campaigns c on c.id=g.campaign_id),'[]'::jsonb)) from base;
$$;
revoke all on function public.dashboard_activity(uuid,integer,integer,text,uuid,text,timestamptz) from public,anon,authenticated;
grant execute on function public.dashboard_activity(uuid,integer,integer,text,uuid,text,timestamptz) to service_role;
notify pgrst,'reload schema';
commit;
