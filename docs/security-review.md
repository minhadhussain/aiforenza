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
