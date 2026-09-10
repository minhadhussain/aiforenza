begin;

-- Operational metadata only: no prompt, secret, invented usage, or wallet mutation.
create table public.request_rejections (
  request_id text primary key,
  user_id uuid not null references public.profiles(id),
  api_key_id uuid not null references public.api_keys(id),
  model_id uuid references public.models(id),
  error_code text not null check (error_code ~ '^[a-z_]{1,80}$'),
  http_status integer not null check (http_status between 400 and 599),
  created_at timestamptz not null default now()
);
create index request_rejections_owner_time on public.request_rejections(user_id,created_at desc,request_id);
alter table public.request_rejections enable row level security;
revoke all on public.request_rejections from public,anon,authenticated;
grant select on public.request_rejections to service_role;

create function public.record_request_rejection(target_request_id text, target_user_id uuid,
  target_api_key_id uuid, target_model_slug text, target_error_code text, target_http_status integer)
returns jsonb language plpgsql security definer set search_path='' as $$
begin
  if not exists(select 1 from public.api_keys where id=target_api_key_id and user_id=target_user_id) then
    raise exception 'request_owner_mismatch';
  end if;
  if target_request_id !~ '^req_[a-f0-9]{32}$' then raise exception 'invalid_request_id'; end if;
  insert into public.request_rejections(request_id,user_id,api_key_id,model_id,error_code,http_status)
    values(target_request_id,target_user_id,target_api_key_id,
      (select id from public.models where slug=target_model_slug),target_error_code,target_http_status)
    on conflict(request_id) do nothing;
  return jsonb_build_object('recorded',true);
end;
$$;
revoke all on function public.record_request_rejection(text,uuid,uuid,text,text,integer) from public,anon,authenticated;
grant execute on function public.record_request_rejection(text,uuid,uuid,text,text,integer) to service_role;

-- One snapshot of financial truth. Higher-priority records override operational ones.
create function public.dashboard_activity(target_user_id uuid, page_size integer default 25,
  page_number integer default 1, filter_model text default null, filter_key uuid default null,
  filter_status text default null, snapshot_at timestamptz default now())
returns jsonb language sql stable security definer set search_path='' as $$
with raw as (
  select u.request_id,u.user_id,u.api_key_id,u.model_id,u.created_at,
    case when u.status='completed' then 'billed' else 'unsettled' end as status,
    u.input_tokens,u.output_tokens,u.cached_input_tokens,u.customer_charge_cents,
    u.reference_charge_cents,u.customer_savings_cents,0::bigint as reserved_cents,
    null::text as error_code,null::integer as http_status,1 as priority
  from public.usage_records u where u.user_id=target_user_id
  union all
  select r.request_id,r.user_id,r.api_key_id,r.model_id,r.created_at,'unsettled',
    null,null,null,null,null,null,r.amount_cents,null,null,2
  from public.wallet_reservations r where r.user_id=target_user_id
  union all
  select r.request_id,r.user_id,r.api_key_id,r.model_id,r.released_at,'released',
    null,null,null,null,null,null,0,r.reason,null,3
  from public.wallet_reservation_releases r where r.user_id=target_user_id
  union all
  select r.request_id,r.user_id,r.api_key_id,r.model_id,r.created_at,'rejected',
    null,null,null,null,null,null,0,r.error_code,r.http_status,4
  from public.request_rejections r where r.user_id=target_user_id
), canonical as (
  select distinct on(request_id) * from raw order by request_id,priority
), enriched as (
  select c.request_id,c.created_at,c.status,c.input_tokens,c.output_tokens,c.cached_input_tokens,
    c.customer_charge_cents,c.reference_charge_cents,c.customer_savings_cents,c.reserved_cents,c.error_code,c.http_status,
    c.api_key_id,k.name as api_key_name,m.slug as model_slug,m.display_name as model_name
  from canonical c
  left join public.api_keys k on k.id=c.api_key_id and k.user_id=target_user_id
  left join public.models m on m.id=c.model_id
), filtered as (
  select * from enriched where created_at<=coalesce(snapshot_at,now())
    and (filter_model is null or model_slug=filter_model)
    and (filter_key is null or api_key_id=filter_key)
    and (filter_status is null or status=filter_status)
), paged as (
  select * from filtered order by created_at desc,request_id desc
  limit greatest(1,least(page_size,100))
  offset ((greatest(1,least(page_number,100000))-1)::bigint * greatest(1,least(page_size,100)))
)
select jsonb_build_object(
  'data',coalesce((select jsonb_agg(to_jsonb(p) order by p.created_at desc,p.request_id desc) from paged p),'[]'::jsonb),
  'total',(select count(*) from filtered),'page',greatest(1,least(page_number,100000)),
  'page_size',greatest(1,least(page_size,100)),'as_of',coalesce(snapshot_at,now()),
  'models',coalesce((select jsonb_agg(to_jsonb(m) order by m.slug) from (
    select distinct model_slug as slug,model_name as name from enriched where model_slug is not null
  ) m),'[]'::jsonb),
  'keys',coalesce((select jsonb_agg(jsonb_build_object('id',k.id,'name',k.name) order by k.created_at desc,k.id)
    from public.api_keys k where k.user_id=target_user_id),'[]'::jsonb)
);
$$;
revoke all on function public.dashboard_activity(uuid,integer,integer,text,uuid,text,timestamptz) from public,anon,authenticated;
grant execute on function public.dashboard_activity(uuid,integer,integer,text,uuid,text,timestamptz) to service_role;
notify pgrst,'reload schema';
commit;
