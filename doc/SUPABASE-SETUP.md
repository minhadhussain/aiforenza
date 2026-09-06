# Supabase Setup

Use this document when preparing a local or hosted Supabase project for the MVP.

## Apply SQL Files

Run these SQL files in order inside the Supabase SQL editor:

1. `infra/supabase/001_profiles.sql`
2. `infra/supabase/002_wallets_transactions.sql`
3. `infra/supabase/003_api_keys.sql`

These files create:

- `profiles`
- `wallets`
- `transactions`
- `api_keys`
- the signup wallet bootstrap RPC for one-time free trial credit

## Required Environment Variables

Copy `.env.example` to `.env` and set at least the following values:

### Web

- `NEXT_PUBLIC_APP_URL`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`

### API

- `API_HOST`
- `API_PORT`
- `API_CORS_ORIGINS`
- `API_KEY_PEPPER`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`

### External Services For Later Phases

- `REDIS_URL`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `AZURE_API_KEY`
- `AZURE_ENDPOINT`
- `LITELLM_MASTER_KEY`
- `SENTRY_DSN`
- `POSTHOG_KEY`
- `POSTHOG_HOST`

## Notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` on the backend only.
- Never commit `.env`.
- `API_KEY_PEPPER` should be a long random secret used when hashing API keys.
- The dashboard uses Supabase sessions, while the model API uses hashed API keys.
