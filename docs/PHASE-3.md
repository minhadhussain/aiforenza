# Phase 3 - Wallet

> Historical phase snapshot. Current total/reserved/available semantics and
> payment evidence: [README.md](README.md).

This phase introduces the financial foundation for the MVP.

## Included

- `wallets` and `transactions` schema for Supabase/PostgreSQL
- idempotent signup wallet bootstrap and one-time `$5.00` trial credit grant
- backend dashboard overview route backed by wallet and transaction data
- dashboard UI wired to live balance and recent transaction data

## Financial Guardrails

- money is represented in integer cents
- wallet balances are constrained to never go negative
- the free-trial grant is tracked with `reference_id = signup:{user_id}`
- wallet balance is derived from immutable transaction activity

## Deferred To Later Phases

- wallet deductions for model usage
- top-ups and Stripe webhook credits
- API key billing linkage
- usage records and provider cost accounting
