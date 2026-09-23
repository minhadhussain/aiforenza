begin;

alter table public.models add column capabilities jsonb not null default '{}'::jsonb
  check (jsonb_typeof(capabilities)='object');

-- Keep the existing single deployment mapping and verified pricing/token limits.
-- The deployed 2026-09-03 Azure Chat API rejects tools with reasoning and max;
-- both are supported by the same deployment's Responses API.
update public.models set capabilities = '{
  "reasoning": true,
  "reasoning_efforts": ["low", "medium", "high", "xhigh", "max"],
  "default_reasoning_effort": "medium",
  "temperature": false,
  "top_p": false,
  "context": 128000,
  "tool_call": true,
  "responses_for_tools": true,
  "responses_efforts": ["max"]
}'::jsonb where slug='gpt-6-astra';

notify pgrst,'reload schema';
commit;
