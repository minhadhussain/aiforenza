# Phase 5 - Model API

> Historical phase snapshot. Current verification uses the configured direct
> Azure gateway, with billing and settlement enabled; see [README.md](README.md).

This phase introduces the OpenAI-compatible model API surface.

## Included

- `models` schema and seed data for the initial curated model list
- `/v1/models` with API-key authentication and OpenAI-compatible output
- `/v1/chat/completions` with model lookup, wallet pre-check, LiteLLM forwarding, and request ids
- streaming and non-streaming proxy support for LiteLLM-backed chat completions

## Notes

- The implementation validates the API key, model, and wallet before forwarding.
- LiteLLM handles provider normalization and forwarding.
- Usage charging and ledger deduction remain deferred to the usage-billing phase.

## Deferred To Later Phases

- atomic usage deductions and usage records
- provider usage reconciliation and billing persistence
- richer model management and pricing administration
