# AI Forenza documentation — start here

Updated 2026-09-10. The website documentation lives at `/docs` and is authored in
`apps/web/lib/docs.ts`. This directory contains operator setup, test evidence and
the original MVP specification.

## Read in this order

1. [Exact setup and top-up steps](SETUP-AND-TOPUPS.md)
2. [Supabase setup and migrations](SUPABASE-SETUP.md)
3. [Local development](LOCAL-DEVELOPMENT.md)
4. [Final API/payment verification](FINAL-E2E-2026-09-10.md)
5. [Production release gates](PRODUCTION-RUNBOOK.md)
6. [OpenCode configuration template](opencode.example.json)
7. [Model chooser and Astra tool compatibility](MODEL-CHOOSER.md)
8. [Usage history, account identity, and request-size limits](USAGE-ACTIVITY.md)

## Current contract

- One active API key accesses all enabled models. Model selection happens in
  OpenCode or the API request, never as an overview activation step. Configure
  OpenCode globally to make AI Forenza available from unrelated projects.

- API: `http://127.0.0.1:8000/v1`; web: `http://127.0.0.1:3000` for local development.
- `npm run dev` starts Next, FastAPI and Docker Redis. It does **not** start Stripe
  forwarding. Keep `npm run dev:payments` running in a second terminal for top-ups.
- Top up **the same account that owns your API key**. Accounts do not share wallets.
- Wallet and package values are USD cents. Stripe collects domestic INR using
  the server's Frankfurter FX quote. INR paise must never be credited as USD cents.
- A Checkout URL or `success=true` is not payment proof. Signed, validated paid
  Checkout events produce one atomic `TOPUP` ledger entry and one wallet credit.
- Available balance = total balance minus outstanding reservations. A new key
  on the same account does not grant another trial or bypass existing holds.
- The current model discount is 40%, applied before upward rounding to cents.
- Real GPT-5.4 streaming/non-streaming and OpenCode requests have been verified.
  Other models remain catalog-driven; listing a model is not this run testing it.

## Evidence versus specification

`MAIN.md` is the original product specification, not a completed-feature checklist.
`PHASE-*.md` are historical implementation notes. Earlier dated verification
reports retain their original observations; later results supersede their current
status claims. Use the final report for this test run, not an old balance snapshot.

Unresolved: historical uncertain holds, refund automation, production HTTPS/load/
security/backup/observability checks, and commercial-use authorization. Local
Stripe test payments move **no real money**. Do not interpret this test as approval
to launch live payments.
