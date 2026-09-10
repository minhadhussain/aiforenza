# Phase 10 - Production

> These are foundations and pending release gates, not a production approval.
> See [PRODUCTION-RUNBOOK.md](PRODUCTION-RUNBOOK.md) and [README.md](README.md).

This phase adds the first practical production-facing work on top of the MVP foundations.

## Included

- backend Sentry initialization hook
- backend PostHog capture helper and key event instrumentation
- basic Redis-backed API rate limiting for model requests

## Operational Follow-Up

- verify Caddy HTTPS deployment in the real target environment
- define backup ownership and restoration procedure for Supabase and any critical config
- run a security review before accepting real customer money
- run load tests against `/v1/models` and `/v1/chat/completions`
- verify Azure commercial-use compliance before launch
