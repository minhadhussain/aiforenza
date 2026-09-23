begin;

-- Verified against the configured Azure deployment on 2026-09-23.
-- GPT-5.4 defaults to none; Sol defaults to medium. Max is Responses-only
-- for Sol and is not supported by GPT-5.4. Keep pricing/limits unchanged.
update public.models set capabilities=capabilities||'{
  "reasoning":true,
  "reasoning_efforts":["none","low","medium","high","xhigh"],
  "default_reasoning_effort":"none",
  "temperature":false,
  "top_p":false,
  "context":128000,
  "tool_call":true,
  "strict_chat_parameters":false
}'::jsonb where slug='gpt-5.4';

update public.models set capabilities=capabilities||'{
  "reasoning":true,
  "reasoning_efforts":["none","low","medium","high","xhigh","max"],
  "default_reasoning_effort":"medium",
  "temperature":false,
  "top_p":false,
  "context":128000,
  "tool_call":true,
  "responses_for_tools":true,
  "responses_efforts":["max"],
  "client_request_timeout_ms":900000,
  "strict_chat_parameters":false
}'::jsonb where slug='gpt-5.6-sol';

notify pgrst,'reload schema';
commit;
