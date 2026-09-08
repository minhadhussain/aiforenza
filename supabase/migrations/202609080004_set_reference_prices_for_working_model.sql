update public.models
set
  input_price_per_million = 5000,
  output_price_per_million = 5000,
  cached_input_price_per_million = 2500,
  customer_input_price_per_million = 3000,
  customer_output_price_per_million = 3000,
  customer_cached_input_price_per_million = 1500,
  discount_percent = 40,
  updated_at = timezone('utc', now())
where slug = 'gpt-5.6-luna';
