# Hackathon $100 promotional credits

## Architecture

The feature adds two tables, `hackathon_campaigns` and `hackathon_team_grants`, and extends the existing wallet/key/ledger/reservation tables. An unclaimed grant row is the organizer's eligible Team ID. Its wallet and API key are created only on claim. The balance remains authoritative in `wallets`; no second balance or reservation implementation is maintained.

Existing integration points:

| Concern | Implementation |
| --- | --- |
| Wallet and availability | `apps/api/app/repositories/wallets.py`, PostgreSQL wallet RPCs |
| Reservations | `reserve_usage`, `record_usage_charge`, `release_unconsumed_usage` |
| Key generation / authentication | `apps/api/app/services/api_keys.py` and existing API-key dependencies |
| Pricing / preflight / settlement | `services/pricing.py`, `services/usage_records.py`, `services/chat_completions.py` |
| Immutable activity | `transactions`, `usage_records`, existing dashboard activity RPC |
| Dashboard authentication | Supabase JWT validation through `get_current_dashboard_user` |
| Dashboard UI | `/dashboard/hackathon`, existing shell, API-key list, and usage activity |

### Claim transaction and database constraints

`claim_hackathon_team` locks the active campaign for share and the eligible Team ID for update. The winner creates one wallet, one key hash, and one `PROMO_GRANT` credit of **10,000 cents**, and marks the Team ID claimed in the same transaction. A waiting concurrent claimant sees the committed claim and receives `team_already_claimed` (HTTP 409). Any insertion failure rolls back all effects.

PostgreSQL enforces:

- At most one active campaign; `(campaign_id, team_id)` unique.
- Grant amount fixed to 10,000 cents.
- Exactly one linked promotional wallet/key for a claimed grant, using unique keys, composite foreign keys, and deferred integrity triggers. Orphan promotional wallets/keys are rejected.
- At most one key **ever** per grant, including revoked keys. No reissue/rotation endpoint.
- Paid wallets have a user owner and no grant; promotional wallets have a grant owner and **no user-wallet owner**.
- Billing scope and claimed Team IDs cannot be reassigned/reset. Promotional ledger/usage history and key material cannot be rewritten or deleted.
- The grant ledger credit is unique per grant, with the amount constrained to 10,000 cents.
- Wallet balances cannot be negative. Promo settlement must equal the reference charge, with zero savings.

The `api_keys.user_id` is retained for audit attribution, rate limiting, and the claimant's existing key-revocation UI. It does not select a paid wallet for promotional requests. Callers supply only the shared bearer key, without a dashboard session or claimant identity.

### Billing and reservations

The centralized model catalog continues to supply reference prices, cached-input prices, provider cost configuration, and pricing limits. `calculate_pricing_breakdown` accepts an authoritative billing source:

- `PAID`: existing catalog discount (currently 40%, multiplier **0.60**).
- `PROMOTIONAL`: multiplier **1.00**, actual charge equals reference charge.

Existing per-request integer-cent rounding is preserved: positive totals round up once, rather than per token. Provider costs remain recorded when known and nullable when the existing catalog has no verified provider cost; they are never invented or substituted with customer prices.

The API key determines the source; client request fields cannot override it. Both streaming and non-streaming routes use the same preflight/pricing/settlement functions. PostgreSQL independently rejects discounted promotional settlements.

Reservations lock the selected wallet and compare its balance against **that wallet's** outstanding holds. Settlement writes the ledger and usage row, deducts the actual charge, and consumes the hold atomically. `usage_records.reserved_amount_cents` and `reservation_created_at` retain the original hold after settlement. Released holds retain their existing audit record. All new activity records receive `billing_source` and `hackathon_grant_id` from the database key/wallet, with campaign attribution available through the grant.

Known provider rejection/connect failures release holds through the existing release RPC. Timeouts, uncertain outcomes, interrupted streams, and missing usage retain holds for the existing reconciliation process. Revoking a key/disablement prevents new admission while allowing already-reserved inference to settle.

Insufficient promotional credit returns the existing **402 / insufficient_balance** error. There is no paid-wallet fallback. Stripe top-ups, personal balances, and personal dashboard financial summaries remain paid-wallet scoped; the Usage page labels promotional activity.

## Deployment and organizer setup

Apply migrations through the project's normal Supabase deployment, or use the existing tracked migration tool from the repository root:

```powershell
python tools/apply_reservations.py 202609120001_hackathon_promotions.sql --validate-only
python tools/apply_reservations.py 202609120001_hackathon_promotions.sql
```

Deploy the migration before the API/frontend code that selects the new columns. Existing history receives the default `PAID` scope without rewriting ledger amounts. The migration has been applied to the configured development database during verification.

Install backend development dependencies for the PostgreSQL tools/tests:

```powershell
python -m pip install -e 'apps/api[dev]'
```

Preload `HACK-001` through `HACK-050` and open claims:

```powershell
python tools/hackathon_admin.py seed --name "Hackathon 2026" --count 50 --prefix HACK --activate
```

Or supply organizer-issued IDs, one per line:

```powershell
python tools/hackathon_admin.py seed --name "Hackathon 2026" --team-ids-file private-team-ids.txt --activate
```

The tool uses private `DATABASE_URL` configuration (process environment or root `.env`) and parameterized SQL. Repeated seeding is idempotent and does not reset claims, create wallets, or issue money. Activating a second campaign fails rather than silently closing the first. IDs normalize to uppercase and allow 3–64 ASCII letters/digits/underscores/hyphens, starting with a letter or digit.

Close new claims:

```powershell
python tools/hackathon_admin.py close --name "Hackathon 2026"
```

**Campaign closure stops new claims; existing grants remain usable.** The claimant may permanently revoke the shared key through the existing API Keys dashboard. An operator can disable a specific grant for incident handling. Neither operation makes its Team ID claimable again.

No organizer campaign is left active by verification. Run the seed command with the intended campaign/IDs before opening the event.

## API contract

Both endpoints require the existing **Supabase dashboard access token**. A Team ID or shared API key is not a dashboard login.

### `POST /v1/hackathon/claim`

```json
{"team_id":"HACK-042"}
```

Only `team_id` is accepted. The backend chooses the campaign, claimant, amount, wallet, and key. Success: **201**, `Cache-Control: no-store`:

```json
{
  "grant": {
    "team_id": "HACK-042",
    "campaign_name": "Hackathon 2026",
    "status": "ACTIVE",
    "promo_balance_cents": 10000,
    "reserved_cents": 0,
    "available_balance_cents": 10000,
    "billing_source": "PROMOTIONAL"
  },
  "plaintext_key": "<one-time shared credential>"
}
```

Errors use the existing dashboard `detail` envelope with `code` and `message`:

| Status | Code / condition |
| --- | --- |
| 401 | Dashboard authentication missing/invalid |
| 404 | `invalid_team_id` |
| 409 | `team_already_claimed` or `campaign_inactive` |
| 422 | Invalid fields, format, or attempted ownership/amount overrides |
| 429 | Existing account/key rate limiter |
| 503 | `hackathon_unavailable`; inspect grant status before retrying |

### `GET /v1/hackathon/status`

Returns `{ "campaign": { "name": "...", "grant_amount_cents": 10000 } | null, "grants": [...] }`, limited to the authenticated claimant. Grants include team/campaign names, total/held/available credit, claim timestamp, status, and key-revoked state. It never returns the secret, hash, or internal wallet/key/grant IDs. Responses are `no-store`.

Shared keys use the unchanged `GET /v1/models` and `POST /v1/chat/completions` paths through central API-key validation. No additional API endpoint, organization, membership, or team role is involved.

## One-time credential behavior

- Cryptographically random, server-generated key using the existing key service and peppered SHA-256 storage pattern. Only its hash and short prefix are stored.
- A key is returned only by a successful claim. Status, duplicate claims, and later key listing never return the secret.
- The UI keeps the revealed secret only in component memory, supports copying/hiding it, and clears it after navigation/reload/account changes/session rejection. It is not saved to browser storage.
- Sentry local-variable collection is disabled to avoid capturing key-creation secrets in exception frames.
- Campaign/team tables and privileged claim/financial RPCs are inaccessible to browser database roles. The backend and database derive billing scope independently of client input.
- Team IDs are first-claim eligibility codes, so organizers should distribute them privately. Merely knowing a claimed Team ID grants no API access.
- If a claim commits but its response is lost, the grant remains claimed. Strict one-time display means the secret cannot be recovered/reissued, and retrying does not mint another grant. This is an intentional first-version limitation.

## Verification

Backend unit/integration coverage is in `apps/api/tests/test_hackathon.py`, `test_hackathon_database.py`, and the existing `test_wallet_database.py` suite. Database tests use random isolated schemas and real PostgreSQL transactions/concurrent connections. They cover all requested claim, pricing, reservation, isolation, audit, security, and concurrency cases, plus rollback, disabled/revoked-key settlement, streamed billing, seeding idempotency, and unchanged Stripe credit targeting.

From `apps/api`:

```powershell
$env:RUN_DATABASE_TESTS='1'
$env:RUN_REDIS_TESTS='1'
python -m pytest -q --tb=short
```

From the repository root:

```powershell
npx --workspace apps/web tsc --noEmit --incremental false
npm --workspace apps/web run build
```

The opt-in live verifier uses real login, browser claim/copy/reload/duplicate handling, model discovery, two bounded provider calls, and SQL ledger verification:

```powershell
python -m pip install playwright
python -m playwright install chromium
# Run the local stack in another terminal: npm run dev
python tools/verify_hackathon_e2e.py
```

It requires no active organizer campaign, creates a dedicated test campaign/account, caps preflight at $0.50 per request, then closes the test campaign, revokes keys, disables test grants, and bans the test account. Financial evidence is retained. It never prints or persists full keys/passwords.

### Recorded results — September 13, 2026

- Backend full suite with PostgreSQL and Redis integrations enabled: **204 passed**, no skips (six existing HTTPX deprecation warnings in Stripe tests).
- TypeScript no-emit check and Next.js production build: **passed**.
- PostgreSQL migration: validate-only rollback and tracked application both **passed**.
- Real browser claim **201**, duplicate **409**, copy and one-time display/reload checks **passed**.
- Model: `gpt-5.6-sol`.
- Promo request `req_be867db1af3c4ee5900ddd4c638da7c7`: **10¢ reference, 10¢ charged**, promotional balance **10,000 → 9,990 cents**; paid wallet unchanged.
- Paid request `req_9ab6a97cb6f04b9c906a589ab552e2bb`: **10¢ reference, 6¢ charged**, paid balance **500 → 494 cents**; promotional wallet unchanged.
- Original reservation provenance, consumed hold, immutable debit, dashboard source labels, and ledger/balance reconciliation: **passed**.

## Changed-file map

- Migration: `supabase/migrations/202609120001_hackathon_promotions.sql`.
- API routing: `apps/api/app/api/router.py`, `api/routes/{hackathon,chat}.py`.
- Repositories: `apps/api/app/repositories/{hackathon,api_keys,dashboard,wallets}.py`.
- Services: `apps/api/app/services/{api_keys,access_control,pricing,usage_records,chat_completions,observability}.py`.
- Backend test setup: `apps/api/pyproject.toml`, `apps/api/tests/{test_hackathon,test_hackathon_database,test_wallet_database}.py`.
- UI: `apps/web/app/dashboard/hackathon/page.tsx`, `apps/web/components/dashboard/{hackathon-panel,dashboard-shell,api-key-panel,usage-activity}.tsx`, `apps/web/lib/{hackathon,api-keys,activity}.ts`.
- Tools: `tools/{hackathon_admin,verify_hackathon_e2e,apply_reservations}.py`.
- Documentation: `README.md`, this runbook.
