# Production Runbook

Use this runbook before allowing real customer traffic or real payments.

## 1. Environment Review

- Confirm `.env` values are set for:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `STRIPE_SECRET_KEY`
  - `STRIPE_WEBHOOK_SECRET`
  - `AZURE_API_KEY`
  - `AZURE_ENDPOINT`
  - `REDIS_URL`
  - `SENTRY_DSN`
  - `POSTHOG_KEY`
  - `POSTHOG_HOST`
- Confirm no secrets are committed to git.

## 2. Database & Backups

- Ensure all Supabase migrations are applied.
- Confirm wallet, transaction, usage, topup, and API key tables exist and match expected schema.
- Confirm a backup and restore plan exists for the production database.

## 3. HTTPS & Reverse Proxy

- Deploy behind Caddy or another HTTPS-capable reverse proxy.
- Verify dashboard and API endpoints are available over HTTPS.
- Confirm correct routing for:
  - `/`
  - `/docs`
  - `/dashboard/*`
  - `/v1/*`

## 4. Billing & Wallet Safety

- Verify new-user free trial grants exactly once.
- Verify Stripe top-up webhook credits exactly once for duplicate delivery.
- Verify insufficient balance returns HTTP 402 without provider forwarding.
- Verify usage deduction and topup credit both produce immutable ledger entries.

## 5. Security Review

- Review API key hashing and storage.
- Review service-role usage to ensure it remains backend-only.
- Review CORS configuration.
- Review request-size handling and model allow-listing.
- Review rate limiting behavior under load.

## 6. Load Testing

- Test `/v1/models` under repeated authenticated reads.
- Test `/v1/chat/completions` under expected concurrency.
- Verify Redis-backed rate limiting works without crashing the API.
- Observe provider timeout behavior and upstream failure handling.

## 7. Observability

- Confirm Sentry receives backend exceptions.
- Confirm PostHog receives key product events such as:
  - `api_key_created`
  - `first_api_request`
  - `topup_started`
  - `topup_completed`

## 8. Launch Compliance

- Verify the Azure account, sponsorship/credit terms, model access terms, and licensing terms permit the intended commercial use.
