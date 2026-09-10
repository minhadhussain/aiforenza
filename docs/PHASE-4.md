# Phase 4 - API Keys

> Historical phase snapshot. Current setup: [README.md](README.md). Keys from the
> same account share one wallet; generating another key does not add funds.

This phase adds the API key lifecycle required for OpenAI-compatible API access.

## Included

- `api_keys` schema for hashed credential storage
- key creation with one-time plaintext reveal
- key listing and revocation for authenticated dashboard users
- backend API key authentication dependency for model-facing routes
- setup notes for applying Supabase schema and environment variables

## Security Notes

- full API keys are never stored in plaintext
- hashes are derived from the key and optional `API_KEY_PEPPER`
- revoked keys are rejected during API authentication
- only the key prefix is returned for later display in the dashboard

## Deferred To Later Phases

- real `/v1/chat/completions` model execution
- usage billing tied to API keys
- admin reporting for API key activity
