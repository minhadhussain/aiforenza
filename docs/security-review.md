# CSS and SQL injection hardening

Date: 2026-10-13. Scope: the requested CSS/SQL injection defenses in the Next.js frontend and FastAPI/Supabase query boundary. This is a focused review and implementation, not a full-system audit.

## Summary

- Production responses now enforce nonce-based script/style CSP, disallow style attributes, and restrict CSS resource loading.
- User-controlled key names, model names, errors, and documentation content continue to use React text rendering. The reviewed app contains no feature that accepts arbitrary user stylesheets or raw HTML.
- SQL/RPC values already use parameter binding. The shared PostgREST client now additionally rejects unexpected filter/projection/sort/mutation grammar before I/O.
- Relevant Next.js, React, PostCSS, Sharp, and source-map dependencies were patched and pinned. Docker installs use the lockfile with `npm ci`.

## Findings and implementation

### INJ-01 — Missing browser injection containment (Medium, defense in depth)

**Evidence:** Before this change, `apps/web/middleware.ts`, `apps/web/next.config.ts`, and `infra/caddy/Caddyfile` set no CSP. The marketing components used inline style attributes for a small set of constant border colors. No attacker-controlled raw CSS/HTML sink was demonstrated; the missing policy would amplify a future HTML-injection defect.

**Implemented:** `apps/web/lib/security-headers.ts:16–45` generates a fresh 128-bit nonce and a policy that:

- Allows same-origin CSS and explicitly nonced framework style elements in production.
- Uses `style-src-attr 'none'` to block markup style attributes.
- Uses nonced scripts and `strict-dynamic`, without production `unsafe-inline` or `unsafe-eval`.
- Restricts images to same-origin/data/blob and fonts to same-origin, preventing CSS from loading attacker-controlled external image/font resources.
- Limits connections to the configured public API and Supabase origins; configuration origins are parsed and reject credentials, wildcard hosts, and CSP punctuation.
- Blocks objects, base-URL changes, and framing; restricts form submissions to the application origin.

`apps/web/middleware.ts:8–40` replaces caller-supplied nonce/CSP headers, forwards the generated policy to Next's renderer, and attaches it to browser responses. Nonce documents receive `private, no-store`. Public auth pages do not perform session-refresh I/O. Dashboard routes retain session checks, including prefetch requests. `apps/web/lib/supabase/middleware.ts` preserves nonce headers and refreshed cookies together.

`apps/web/app/layout.tsx:8–9` opts into request-time rendering. Constant style attributes were replaced with CSS classes in `globals.css`, the homepage, models page, and shared public components. The pointer glow continues to set individual CSSOM properties from numeric mouse coordinates; it does not parse user CSS.

**Limits:** A CSP nonce is not a sanitizer. `strict-dynamic` intentionally trusts scripts loaded by already-authorized JavaScript; arbitrary JavaScript execution is outside the CSS containment boundary. New raw-HTML or theme-editing features would require separate design and sanitization. Nonce-based pages require dynamic rendering and should not be cached as shared HTML by an upstream CDN.

### INJ-02 — Query grammar lacked a central allowlist (Low, defense in depth)

**Evidence:** The existing helper encoded PostgREST filter values and validated table/RPC path syntax but accepted arbitrary query dictionaries. Existing repositories construct these dictionaries themselves; no public route forwarding arbitrary client dictionaries was found, and no remotely exploitable raw-SQL injection was demonstrated.

**Implemented:** `apps/api/app/repositories/supabase_rest.py:24–54` checks query keys, values, filter operators, projections, ordering, and limits. `rest_select` and `execute_rest_mutation` enforce the check (`:78–114`). Logical filters, broad operators, unapproved query controls, duplicate-value lists, invalid projections, and mutation preferences fail before database I/O. PATCH still requires an explicit equality ID target.

**Retained controls:** HTTPX query encoding, JSON RPC arguments, static parameterized SQL, psycopg2 value binding in organizer tools, UUID/model validation, ownership predicates, and database error redaction. SQL keywords and apostrophes in ordinary text are not removed. See [SQL/filter injection prevention](sql-injection-prevention.md).

**Limits:** This helper is not a general-purpose client query interface or an authorization mechanism. Repository-owned identifiers/projections, tenant predicates, database RLS, and restricted RPC privileges remain necessary. No schema or live security-policy migration was required for these changes.

### INJ-03 — Vulnerable framework/CSS dependencies (Critical package advisory, patched)

**Evidence:** The initial production `npm audit` flagged Next.js 15.4.0, including [RSC remote code execution](https://github.com/advisories/GHSA-9qr9-h5gf-34mp) and [nonce-related XSS](https://github.com/advisories/GHSA-ffhc-5mcf-pf4q), plus PostCSS [style-breakout](https://github.com/advisories/GHSA-qx2v-qp2m-jg93) and source-map processing advisories. Advisory presence establishes an affected package version, not proof that every listed feature is reachable in this deployment.

**Implemented versions:** Next.js 15.5.27; React/React DOM 19.1.9; PostCSS 8.5.29; Sharp 0.35.5; source-map-js 1.2.2. Root overrides ensure Next's nested CSS dependency and React peer dependencies also resolve to these versions. The local dev launcher resolves Next from the web workspace to support either hoisted or workspace-local installations.

## Verification

- `npm --workspace apps/web run test:auth`: 14 passing auth/PKCE/middleware tests.
- `npm --workspace apps/web run test:security`: 6 passing tests for production/development CSP, origin validation, nonce replacement, refreshed-cookie forwarding, and escaped hostile API-key names.
- `npm --workspace apps/web run build`: successful production compilation and type checking. Existing Supabase Edge-runtime compatibility warnings remain.
- `python tools/verify_injection_prevention.py`: real Chromium enforcement against a local production build on port 3100. Checks seven public pages, unique matching framework nonces, hydration, login/signup links, model search, hostile synthetic API text, blocked style attributes/inline styles/external CSS/CSS image requests, blocked parser-inserted scripts, and allowed nonced styles. Synthetic responses are browser-local; no attack payloads are written to real accounts.
- `python tools/verify_signin.py --url http://127.0.0.1:3000`: real password sign-in and session reload succeeded with zero browser errors.
- `RUN_DATABASE_TESTS=1 python -m pytest tests/test_query_safety.py tests/test_query_safety_database.py -q -p no:cacheprovider` (from `apps/api`): 75 passed, including two real PostgreSQL tests in an isolated schema. Confirms literal SQL-shaped values, intact tables, correct wallet effects, and no cross-user filter broadening.
- Remaining backend suite: 300 passed, 11 opt-in integrations skipped. The two query-specific PostgreSQL integrations above were explicitly enabled and passed.
- `npm ci --ignore-scripts --dry-run`: lockfile/install validation succeeded.
- `npm audit --omit=dev`: zero known production dependency vulnerabilities at verification time.

## Development and deployment notes

- `npm run dev` needs Next's local HMR/overlay exceptions: inline style **elements**, script `unsafe-eval`, and loopback WebSocket connections. Style attributes remain blocked. Production behavior must be tested with `next build` and `next start`; do not expose the dev server as production.
- Public API and Supabase URLs must be correctly configured for the web build/deployment; external CSS/font/image services are not allowlisted by default. Google OAuth uses navigation rather than embedded scripts, and hosted Stripe Checkout remains a navigation.
- The complete npm audit still reports seven development-tooling findings in Tailwind's glob/parser dependency tree (five high, two moderate). They are not included in the clean production audit; a Tailwind tooling migration was not performed.
- Hosted CDN/header configuration, a complete Google identity-provider login, Docker image execution, and a full Python dependency-advisory audit were not verified in this focused task. No Python advisory scanner was installed.

## BUILD 2026 repeat-claim review — 20 October 2026

Scope: repeated use of one Team ID after refresh, cleared browser storage, fresh sessions/devices, changed IP headers, account switching, concurrency, depleted credit, key revocation, and campaign closure/reopening.

### CLM-01 — Duplicate grants prevented by durable database state (verified control)

No duplicate-grant bypass was found in the reviewed path. `apps/api/app/api/routes/hackathon.py` authenticates the dashboard identity, normalizes the Team ID, rejects extra ownership/campaign/amount fields, and calls the privileged claim RPC. Browser state and IP addresses do not decide whether a grant is available.

`supabase/migrations/202609120001_hackathon_promotions.sql:172–194` locks the selected campaign/Team ID row with `FOR UPDATE` and rejects any status other than `UNCLAIMED`. Grant creation, its promotional wallet, its hashed spending key, and the $100 ledger credit occur in one transaction. Unique constraints protect campaign/Team ID, grant/wallet, grant/key, and the grant-credit ledger row (`:11–48`). Claim identity cannot be reset or reassigned after claiming (`:66–80`), and browser roles cannot execute the claim RPC directly (`:193–194`).

**Deployed verification:** read-only inspection confirmed the row lock and claimed-team rejection in the installed function, four valid unique indexes, enabled RLS, enabled claim-immutability/integrity triggers, and RPC execution denied to `anon`/`authenticated` while allowed to `service_role`.

**Regression evidence:** the new HTTP-to-PostgreSQL test in `apps/api/tests/test_hackathon_database.py` sends 32 attempts with up to eight concurrent workers, two simulated verified identities, fresh HTTP clients, case/whitespace variations, and differing cookie/IP/user-agent headers. It then spends the entire allocation through the reservation/settlement RPCs, revokes the key, disables the grant, closes/reopens the same campaign, and sends eight more claims. The final state has exactly one grant, one wallet at zero, one key, and one $100 grant-credit entry, with the original claimant and claim timestamp intact. All database writes are confined to an isolated test schema.

### CLM-02 — Repeat-request throttling is account-bound (verified control)

The existing Redis throttle uses the verified account ID and a server-constructed claim key, not caller-supplied cookies or IP headers (`apps/api/app/api/routes/hackathon.py:61–70`, `apps/api/app/services/rate_limit.py:17–45`). A new real-Redis route test verifies that fresh clients, changed session-token fixtures, and changed forwarding headers cannot reset the same account's counter. Rate-limit and access-check failures return 429/503 before key generation, profile lookup, or the claim RPC. Database uniqueness continues to protect credits if counters expire or a different account sends the request.

**Changes:** added these regression tests, clarified the duplicate-claim API error, and documented the same policy in the BUILD 2026 participant FAQ. The already-deployed database protection did not require a new financial migration.

**Checks:** 34 targeted API, real PostgreSQL, and real Redis tests passed with `RUN_DATABASE_TESTS=1 RUN_REDIS_TESTS=1`. The tests substitute identity verification but exercise the actual claim route and transaction; they do not assert that a VPN itself was detected or blocked.

**Boundary:** eligibility remains possession of an organizer-enabled claim code, not proof of project membership. This review establishes one allocation per campaign/Team ID; organizers must map each project to one eligible code and keep unclaimed codes private. A separate future campaign intentionally has its own eligibility and grant records.

## Paid API credential and cost review — 20 October 2026

Scope: the user's credential-exposure, paid-proxy authorization, request-budget, and verified-signup checklist. Framework versions remain FastAPI 0.116.1, Next.js 15.5.27, and React 19.1.9. Operational guidance is in [paid API safety](paid-api-safety.md).

### COST-01 — Secrets could enter Docker build layers (High, fixed)

**Evidence:** the repository had no `.dockerignore`; the web builder used `COPY . .`, and the web service received the entire root `.env`. Git ignore rules do not exclude files from Docker contexts. Sharing builder layers or access to the web runtime environment could expose backend/provider credentials. No such external disclosure was demonstrated.

**Fix:** added Docker context exclusions, limited the web image's copied source directories, passed only public web build arguments, and replaced the web runtime's full secret environment with an explicit configuration allowlist. Workspace-local npm dependencies are copied from the controlled dependency stage. An internal API URL supplies container-to-container server requests without exposing secrets to clients. Git ignore rules now cover other `.env.*` variants too.

### COST-02 — Direct provider-proxy access bypassed application spending checks (High, fixed)

**Evidence:** `docker-compose.yml` published LiteLLM's port 4000 on all host interfaces, while `infra/docker/litellm.config.yaml` had no master-key requirement. That deployment path could accept provider requests outside the FastAPI wallet/rate-limit pipeline. Exploitability required that Compose service to be running and reachable; the local development launcher starts only Redis alongside the application servers.

**Fix:** removed the published proxy port, restricted its environment to the Azure/proxy settings, configured master-key authentication, and made empty-key startup fail. The proxy remains available to the API on the private Compose network.

### COST-03 — Non-strict models forwarded arbitrary extra fields (Medium, fixed)

**Evidence:** `ChatCompletionRequest` accepts SDK extras, and `normalize_model_payload` previously returned them unchanged for non-reasoning models or lightly modified for non-strict reasoning models. This included client-supplied routing/credential parameters and options for capabilities outside the current text-only pricing contract. The model slug and wallet were already validated, but arbitrary outbound fields were not globally constrained.

**Fix:** applied a metered-Chat field allowlist and message-field allowlist to every model. Hosted/non-function tools are rejected before reservation/inference; supported client function calls and existing model-specific reasoning variants remain available. Upstream model IDs and URLs still come exclusively from server configuration/catalog data.

### COST-04 — Verified-email policy depended entirely on hosted configuration (Medium, hardened)

**Evidence:** hosted auth has confirmation enabled, but local Supabase had it disabled, and the backend accepted any returned Supabase user without checking the authoritative confirmation timestamp. An unverified identity returned by a non-confirming/custom auth configuration could otherwise reach account/key/credit operations.

**Fix:** local confirmation is enabled; the backend rejects unconfirmed emails before these operations, ignores user-editable verification metadata, and the account-setup screen explains how to confirm before retrying. The rate-limit defaults are now 20/minute per account and per key. Existing transactional trial/project grant limits are preserved.

### Preventive checks and evidence

- Next startup/build rejects recognizable private credentials under public environment prefixes; Supabase anon/publishable and Stripe publishable keys remain accepted. Errors print variable names only.
- Checked configured private credential values against **688 Git history blobs** and **83 existing browser asset files**: no matches. Public environment values contained no detected private key or privileged JWT. This exact-value check does not establish that no unknown/retired credential ever appeared in history.
- Only `.env.example` is tracked. Git checks confirm local/production environment files are ignored and the template remains trackable.
- Read-only hosted checks confirmed email confirmation is required and **zero active API keys** belong to unconfirmed email identities.
- Compose configuration resolves successfully, with an allowlisted web environment and no published LiteLLM port. No provider secrets are printed by the verification.
- Backend regression suite: **397 passed**, 15 opt-in database/Redis tests skipped. The two real-Redis limit tests were then enabled separately and passed. Frontend checks: **18 auth tests**, **9 security tests** passed. The real password login, logout, deep-link return, autofill, and session-reload checks passed.
- TypeScript no-emit validation passed. `npm audit --omit=dev` reported zero production dependency vulnerabilities. The full Docker build remains unverified: the first attempt failed in Google's font loader; the Node 22 retry reached the build step but exceeded the 300-second command timeout. Node 22 also meets the installed Supabase storage package's runtime requirement.

Provider billing alerts, hard spending limits, prepaid auto-recharge, unknown historic credentials, and multi-account identity uniqueness remain external/operational controls. No provider billing configuration was changed, no provider credit was spent for verification, and no key rotation was necessary based on the configured-secret checks.
