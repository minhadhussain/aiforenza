# Paid API credentials and cost controls

## Credential boundaries

- Azure/OpenAI/Anthropic credentials, Stripe secret and webhook keys, Supabase service-role/secret keys, the API-key pepper, database credentials, and the LiteLLM master key belong in private server environment variables or the deployment's secret store.
- Never use `NEXT_PUBLIC_`, `VITE_`, `EXPO_PUBLIC_`, or `REACT_APP_` for those values. Next startup/build now rejects recognizable secret values, secret variable names, privileged/session JWTs, and public copies of private environment values. Supabase **anon/publishable** and Stripe **publishable** keys are intentionally public.
- `.gitignore` excludes `.env` and `.env.*`, with `.env.example` as the empty template exception. `.dockerignore` also excludes environment files, local test credentials, Git history, and generated output from build contexts. The web image copies only its application/shared sources and receives four explicit public build arguments.
- The web container receives public configuration plus `API_INTERNAL_BASE_URL`; it does not receive the root backend secret environment. Only the API and internal provider proxy receive the upstream credentials they need.
- Application examples read customer keys from private environment variables or OpenCode's credential store. The dashboard shows a customer's newly generated key once to that authenticated customer; platform/provider keys are never part of that response.

If a credential is exposed in a commit, image, log, screenshot, or chat, revoke/rotate it at the issuing service and update the private deployment setting. Removing the text from the current file or Git history does not revoke it. Do not paste real keys into coding-assistant prompts.

## Server-enforced paid request flow

Customers send requests to AI Forenza's API using their own revocable platform key. The backend authenticates that key, checks its account and wallet, enforces per-account/per-key rate limits and concurrency, resolves a server-approved priced model, validates request controls, and atomically reserves the maximum authorized charge **before** contacting an upstream provider.

- Default rate limits: **20 requests/minute per account and per key**, configured through `API_REQUESTS_PER_MINUTE_PER_USER` and `API_REQUESTS_PER_MINUTE_PER_KEY`. All keys belonging to the same account share its account limit. Redis access-check failures fail closed.
- Incoming request bodies are capped before JSON parsing (default 1,000,000 bytes), and message counts are capped (default 100).
- Input/output token allowances must fit the catalog's pricing limits. Omitted output limits default to 1,024 tokens; supplied limits cannot exceed the approved model ceiling. Only one completion and standard service pricing are admitted.
- Customers can select only an enabled, priced **public model ID**. The backend selects the actual provider/deployment and endpoint. Changing a request's model or parameters never skips the corresponding cost authorization.
- Every model uses an outbound field allowlist. Client-provided API keys, routing URLs, provider overrides, unmetered hosted search/audio options, and previous provider conversation IDs are not forwarded. Tool declarations are limited to client-executed functions; supported legacy function calling remains available on compatible models.
- Actual provider usage determines settlement. Missing usage or uncertain inference keeps the reservation for reconciliation instead of inventing a free result or refund.

The browser communicates with AI Forenza and Supabase's public authentication API, not directly with Azure/OpenAI/Anthropic using platform credentials. Python, CLI, and other customers use the same authenticated, metered API.

## Docker provider proxy

LiteLLM is reachable only on the internal Compose network and requires a private `LITELLM_MASTER_KEY`. Set a strong randomly generated master key in the server secret store before starting that service. An empty value stops the proxy at startup. The API uses the same private key when LiteLLM is the configured transport.

The API remains the customer-facing inference entrypoint. Do not publish LiteLLM port 4000 or add a reverse-proxy route that bypasses AI Forenza's wallet and rate checks.

Public Next.js values are supplied at build time, for example by `docker compose build web`. Rebuild the web image when changing those public values. Server-side requests inside Compose use `API_INTERNAL_BASE_URL=http://api:8000/v1`; browsers use the public API URL.

## Signup credits

Hosted Supabase currently requires email confirmation. Local Supabase configuration now requires it too, with an eight-character password minimum. The backend checks Supabase's authoritative `email_confirmed_at` before account initialization, credit claims, or key creation; a user-editable `email_verified` metadata field cannot substitute for it.

The existing **$5 one-time trial per account** and **one $100 BUILD 2026 allocation per eligible project code** remain database-controlled. Email verification reduces unverified signup abuse but does not establish that two verified accounts belong to different people. Keep free allowances bounded and monitor issuance. BUILD 2026 codes must be issued once per selected project.

## Provider dashboard controls

These settings are outside this repository and have not been changed or verified by application tests:

1. Configure budgets and billing alerts in Azure or each upstream provider's dashboard.
2. Use hard spending limits or prepaid balance caps where the provider actually supports them. Azure budget alerts are notifications, not an automatic hard spending cutoff.
3. Keep provider auto-recharge disabled or tightly limited when using prepaid providers.
4. Restrict credentials to the required projects/resources and keep an operational revocation procedure.

The customer wallet checks are not a substitute for upstream account-level controls.
