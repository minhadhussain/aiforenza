# API, billing, and pricing verification

> Historical report. Later tests supersede old pricing/alias, Stripe and browser
> limitations below. Current evidence: [FINAL-E2E-2026-09-10.md](FINAL-E2E-2026-09-10.md).

## Verified in this implementation pass

- `python -m pytest -q` with `RUN_DATABASE_TESTS=1 RUN_REDIS_TESTS=1`: **75 passed**.
- PostgreSQL tests use an isolated random schema and remove it afterward. They exercise the actual reservation/settlement functions, not a Python imitation of row locking.
- Two simultaneous 40-cent reservations against 50 cents: only one succeeds.
- Duplicate concurrent settlement: one charge and the same transaction returned.
- Exact-balance settlement reaches zero, and subsequent reservations fail.
- Duplicate payment event: one TOPUP and exactly 1,000 cents credited for a 1,000-cent payment fixture.
- Redis Lua tests exercise concurrent acquisition and configured limits against real local Redis.
- `python tools/verify_api.py`: real Supabase user/session, generated AI Forenza key, real Azure non-streaming and streaming completions, persisted usage, and revocation checks succeeded.
- Live wallet result: **500 → 492 cents**, two usage records. Test identity disabled; generated key revoked. Financial history retained.
- `npm --workspace apps/web run build`: passed, including TypeScript checking.

## Changes

- Reservations in PostgreSQL prevent multiple requests authorizing the same funds. Settlement still writes the existing wallet/transaction/usage tables atomically.
- New migrations: `202609090001_wallet_reservations.sql`, `202609090002_payment_credit_safety.sql`; applied and recorded in Supabase migration history.
- Cached tokens are a subset of prompt tokens, not additional input. They are billed once. Total tokens exclude double-counted cache tokens.
- Decimal pricing applies the configured model discount once; reference and customer totals round up once to wallet cents. Savings equals the difference in rounded totals. This means tiny positive-price requests cost at least one cent; effective small-request discounts may differ due to cent rounding.
- Model serialization uses Decimal-derived rates. Public models/pricing now load the backend catalog and show only enabled models with sourced benchmark prices, with an explicit unavailable state instead of static fallback rates.
- Tool-call fields are preserved; absent output limits get an enforced 1,024-token limit. Text-only input is conservatively budgeted using UTF-8 payload bytes plus message overhead; `n != 1` and multimodal input are rejected until supported bounds exist.
- Streaming SSE parsing buffers fragmented lines; final provider usage is required. DONE is emitted after successful settlement. Concurrency slots last through iteration.
- Redis failures fail closed (503), and concurrency acquisition is atomic across user/key counters.
- Provider errors are sanitized; public responses omit provider routing data and use the public model slug.
- Request body limit is enforced before parsing; metadata-only logs carry request ID, status, latency, and authorized user/key/model identifiers.
- Key reveal supports Copy and Hide; no full key is persisted in browser storage.
- Auth redirects preserve refreshed cookies; login return paths are restricted; logout uses a 303 redirect.
- Dev/build output directories are separate (`.next-dev` / `.next`) to avoid concurrent build corruption.

## OpenCode

Use `docs/opencode.example.json` as a template for the client's project `opencode.json`.
It uses `@ai-sdk/openai-compatible`, a custom provider called `aiforenza`, and
`http://localhost:8000/v1`. Set `AI_FORENZA_API_KEY` locally to your generated key.
Do not send this key to OpenAI or Azure directly. The template uses Sol under its
own name; change to another enabled, verified public model ID as appropriate.
Do not assume `OPENAI_BASE_URL` is honored by every built-in OpenCode provider.

Sources checked: https://opencode.ai/docs/providers/ and https://opencode.ai/docs/config/.
Native Claude Code uses a different protocol; direct compatibility is not verified.

## Local execution

1. Start Docker Desktop; run `docker compose up -d redis`.
2. From repo root: `python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --env-file .env`.
3. From repo root: `npm --workspace apps/web run dev -- --port 3000`.
4. Local `.env` uses `REDIS_URL=redis://127.0.0.1:6379/0`; Compose overrides it to the container hostname.
5. Run `python tools/verify_api.py` for bounded real provider verification. It creates/revokes its own test key and never prints credentials.

## Not complete / not claimed

- Stripe Checkout → CLI forwarding → browser return → wallet update has **not** been verified end-to-end here. Tests prove signature/state checks and DB credit idempotency, not Stripe account eligibility. Existing account restrictions still need resolution.
- Refund workflows, automated failed/expired top-up reconciliation, and a protected internal admin interface remain incomplete.
- Pricing currently includes earlier test rates. This pass did **not** assert they are real vendor prices or overwrite business pricing. Approved reference rates and provider-cost sources are still required; provider cost remains nullable/internal.
- Earlier verification mapped Luna to Sol in the database. This pass preserves that existing mapping but does **not** certify Luna inference. Product aliases should be corrected/explicitly labeled before launch; unavailable models must be disabled.
- Uncertain provider failures, missing usage, cancellations, and process crashes retain PostgreSQL holds; operators must reconcile them against provider evidence. No fabricated usage or automatic expiry permits re-spending. Automated reconciliation remains a launch blocker.
- Redis concurrency counters intentionally have no unsafe short expiry. After a process crash, reconcile stale counters only after confirming no requests remain. Durable lease/reconciliation automation is outstanding.
- The conservative input budget is not a universal tokenizer guarantee. Unsupported modalities are rejected, but provider limit compliance and per-model metering must be certified before claiming unlimited production safety.
- Existing historical reference/savings backfill and immutable-ledger enforcement require a separate data review; this pass did not rewrite historical records.
- Verified benchmark-priced and callable models are now limited to GPT-6 Astra, GPT-5.6 Sol, GPT-5.4, and Grok 4.6. DeepSeek V4 Pro is callable but still disabled until a trusted benchmark rate is approved. GPT-5.6 Luna, DeepSeek V4 Flash, and Kimi K2.7 Code are disabled because they failed provider verification on the current Azure resource. The earlier Luna→Sol verification alias has been removed from the catalog configuration.
- Full browser automation was unavailable (Playwright not installed). Builds/typechecks and real backend tests are not a substitute for browser end-to-end coverage.
- Aggregate dashboard rollups still have record limits; all-time totals above those limits need database aggregation.
- Production HTTPS, dependency/security audit, backup restore drill, load testing, full observability delivery, and commercial-use authorization remain outstanding.

This is a verified corrective pass, **not a declaration that the whole MVP is complete or safe to launch with real customer money**.
