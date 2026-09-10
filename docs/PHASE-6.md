# Phase 6 - Usage Billing

> Historical phase snapshot. Current verified accounting: [README.md](README.md).

This phase adds the first billable usage foundation on top of the model API.

## Included

- `usage_records` schema and RPC for atomic usage charging
- customer pricing fields on `models`
- preflight balance estimation before provider forwarding
- non-streaming and streaming usage capture with post-response charging
- usage charge persistence into both `transactions` and `usage_records`

## Notes

- pricing is model-driven, not hard-coded globally
- charging is keyed by `request_id` for idempotency
- current settlement requires authoritative provider usage; no estimated-usage
  fallback is permitted. Missing usage retains the reservation for reconciliation.

## Deferred To Later Phases

- richer provider-cost reconciliation
- detailed dashboard usage analytics
- Stripe-funded usage lifecycle after top-ups
