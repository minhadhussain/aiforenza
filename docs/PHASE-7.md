# Phase 7 - Stripe

> Updated workflow: [SETUP-AND-TOPUPS.md](SETUP-AND-TOPUPS.md).
> Real hosted Checkout, signed HTTP webhook, USD credit, duplicate replay and
> post-top-up API verification: [FINAL-E2E-2026-09-10.md](FINAL-E2E-2026-09-10.md).

This phase introduces prepaid top-ups through Stripe Checkout.

## Included

- `topups` and `stripe_events` schema
- atomic wallet credit RPC for verified Stripe completions
- Stripe Checkout session creation for fixed MVP amounts
- webhook signature verification and idempotent completion handling
- dashboard Add Funds surface and top-up history panel

## Notes

- wallet crediting happens only after a verified webhook event
- duplicate webhook delivery is handled through unique Stripe event ids
- top-up amounts are constrained to the fixed MVP options
- Stripe collects INR; the wallet receives the chosen USD package amount.
- Run `npm run dev:payments` as well as `npm run dev` for local webhook delivery.
- An API-created Checkout URL is unpaid until Checkout and any authentication finish.
- Both completed-paid and asynchronous-paid events can fulfill; unpaid events
  cannot credit. Refund and failed/expired reconciliation remain deferred.

## Deferred To Later Phases

- refunds and refund webhook handling
- custom top-up amounts
- advanced payments analytics in the dashboard
