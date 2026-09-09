alter table public.topups
  add column if not exists stripe_currency text;

update public.topups
set stripe_currency = coalesce(stripe_currency, 'INR')
where stripe_currency is null;

alter table public.topups
  alter column stripe_currency set not null;
