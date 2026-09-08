update public.models
set provider_model_id = case slug
  when 'gpt-6-astra' then 'gpt-6-astra'
  when 'gpt-5.6-sol' then 'gpt-5.6-sol'
  when 'gpt-5.6-luna' then 'gpt-5.6-luna'
  when 'grok-4.6' then 'grok-4.6'
  when 'deepseek-v4-pro' then 'DeepSeek-V4-Pro'
  when 'deepseek-v4-flash' then 'DeepSeek-V4-Flash'
  when 'kimi-k2.7-code' then 'Kimi-K2.7-Code'
  when 'gpt-5.4' then 'gpt-5.4'
  else provider_model_id
end
where slug in (
  'gpt-6-astra',
  'gpt-5.6-sol',
  'gpt-5.6-luna',
  'grok-4.6',
  'deepseek-v4-pro',
  'deepseek-v4-flash',
  'kimi-k2.7-code',
  'gpt-5.4'
);
