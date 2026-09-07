alter table public.models
  add column if not exists customer_input_price_per_million numeric(12,4),
  add column if not exists customer_output_price_per_million numeric(12,4),
  add column if not exists customer_cached_input_price_per_million numeric(12,4);

update public.models
set
  customer_input_price_per_million = coalesce(customer_input_price_per_million, input_price_per_million),
  customer_output_price_per_million = coalesce(customer_output_price_per_million, output_price_per_million),
  customer_cached_input_price_per_million = coalesce(customer_cached_input_price_per_million, cached_input_price_per_million, 0)
where customer_input_price_per_million is null
   or customer_output_price_per_million is null
   or customer_cached_input_price_per_million is null;

alter table public.models
  alter column customer_input_price_per_million set not null,
  alter column customer_input_price_per_million set default 0,
  alter column customer_output_price_per_million set not null,
  alter column customer_output_price_per_million set default 0,
  alter column customer_cached_input_price_per_million set default 0;
