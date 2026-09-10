# Phase 2 - Authentication

> Historical phase snapshot. Current steps and status: [README.md](README.md).

This phase adds the initial authentication foundation described in the MVP specification.

## Included

- Supabase browser, server, and middleware client helpers for the web app
- login and signup flows
- protected dashboard layout and auth-aware routing
- backend bearer-token validation for dashboard APIs
- initial `profiles` table SQL for Supabase/PostgreSQL

## Notes

- The model API remains API-key based and is not coupled to Supabase sessions.
- The dashboard side uses Supabase sessions for authenticated user access.
- Profile creation sync and wallet initialization are deferred to the wallet phase.

## Deferred To Later Phases

- free trial wallet creation
- API key creation and revocation
- Stripe top-up flow
- usage history and transaction views backed by real data
