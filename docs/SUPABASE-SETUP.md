# Supabase Setup

Use this document when preparing a hosted Supabase project. Start with
[SETUP-AND-TOPUPS.md](SETUP-AND-TOPUPS.md) for the full application workflow.

## Apply SQL Files

The canonical migration history is **all files in `supabase/migrations/`, in
timestamp order**, currently through `202609110001_request_activity.sql`.
Do not use the seven old `infra/supabase` snapshots as a complete setup.

From the repository root:

```powershell
npm exec supabase -- login
npm exec supabase -- link --project-ref YOUR_PROJECT_REF
npm exec supabase -- migration list
npm exec supabase -- db push --dry-run
```

Verify the target project and review pending SQL, including historical catalog
seeds, before running `npm exec supabase -- db push`. On an existing project,
do not rerun already-applied migrations or automatically repair history. Back up
first. Never run `db reset` on the shared/hosted financial database.

These files create:

- `profiles`
- `wallets`
- `transactions`
- `api_keys`
- `models`
- `usage_records`
- the signup wallet bootstrap RPC for one-time free trial credit
- the follow-up wallet bootstrap function fix migration
- the atomic usage charge RPC and model-level customer pricing fields
- `topups`, `stripe_events`, INR collection/USD credit metadata and `complete_topup`
- `wallet_reservations`, `wallet_reservation_releases`, `reserve_usage`,
  `wallet_availability`, and audited `release_unconsumed_usage`

After migration, confirm RLS and service-role-only RPC permissions, then configure
Supabase Auth email confirmation plus site/redirect URLs matching the frontend.
Review model rows after applying historical seeds: only verified/priced enabled
models may be served. Do not infer current model availability from old seed SQL.

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

### External Services Required For Current Features

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
- Set an API-key pepper before first key issuance if desired; never change an
  existing pepper casually, because it changes authentication hashes.
- The dashboard uses Supabase sessions, while the model API uses hashed API keys.
