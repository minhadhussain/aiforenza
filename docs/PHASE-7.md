# Phase 7 - Stripe

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

## Deferred To Later Phases

- refunds and refund webhook handling
- custom top-up amounts
- advanced payments analytics in the dashboard
