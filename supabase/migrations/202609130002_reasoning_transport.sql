begin;

-- Long-horizon Astra effort can exceed the client's five-minute default.
-- This is a client timeout recommendation, not a token limit or price multiplier.
update public.models set capabilities=capabilities||'{"client_request_timeout_ms":900000}'::jsonb
where slug='gpt-6-astra';

-- OpenCode sends medium effort for GPT-5 models even without explicit variants.
-- Azure Sol rejects that combination with tools on Chat, but accepts Responses.
-- Explicit none and all tool-free Sol requests retain their existing Chat route.
update public.models set capabilities=capabilities||'{"responses_for_tools":true}'::jsonb
where slug='gpt-5.6-sol';

notify pgrst,'reload schema';
commit;
