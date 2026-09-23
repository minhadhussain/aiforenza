---
name: aiforenza-security-review
description: "Use for an explicit security audit, threat model, or security-hardening request for AI Forenza. Covers its FastAPI API, Next.js/Supabase authentication, database RLS and privileged RPCs, API keys, Stripe payments, hackathon grants, wallet reservations, usage ledger, model proxy, and OpenCode setup. Not for routine feature work or merely installing skills."
---

# AI Forenza system security review

Use the installed security skills to produce a repository-grounded review and, when requested, focused fixes. Installing these skills is preparation, not proof that the application has been audited or secured.

## Start with the actual system

Read `README.md`, the relevant guides in `docs/`, `apps/api/pyproject.toml`, and `apps/web/package.json`. Locate current routes, repositories, services, migrations, tests, and deployment settings before making architectural claims.

The framework references describe newer framework versions in places. Check this project's installed versions and current upstream advisories before recommending APIs, dependency upgrades, or migration steps. For example, do not rename Next.js middleware or upgrade frameworks solely to match a reference document's version.

Separate local development from public production deployment. Record material unknowns rather than assuming an edge proxy, Google provider, Stripe webhook, or public API URL is configured correctly. Do not classify an intentionally local HTTP URL as a production TLS vulnerability without evidence of public exposure.

## Load the appropriate downloaded skills

- `security-best-practices`: read its FastAPI, Next.js, React, and general frontend references. Trace authentication and authorization through both application layers.
- `security-threat-model`: map assets, entry points, trust boundaries, plausible attackers, and existing mitigations. Follow its evidence and context-validation requirements.
- `supabase-postgres-best-practices`: prioritize `security-privileges.md`, `security-rls-basics.md`, `security-rls-performance.md`, `schema-constraints.md`, and the `lock-*.md` references when reviewing migrations and financial RPCs.
- `property-based-testing`: use meaningful invariants and adversarial input generation where appropriate. Prefer existing tools; add a test dependency only when its value and scope are agreed.

These are local skills, not Claude plugins. No external agents, plugins, or remote analysis services are required by this workflow.

## Review coverage

### Identity and browser boundary

- Email/password signup/login, Google OAuth startup, PKCE verifier/session cookies, callback errors, safe return URLs, logout, and session refresh.
- Server-side validation of Supabase identity and account initialization. Never trust a client-supplied user ID, email, campaign owner, wallet ID, or billing source.
- Route-level authorization independent of page navigation, authenticated response caching, CSRF where ambient cookies authorize state changes, CORS, and XSS.
- Preserve the supported Supabase SSR/browser token-refresh pattern; evaluate cookie controls in that context instead of blindly changing flags and breaking authentication.

### Spending credentials and model gateway

- API-key entropy, server-side generation, hashing/pepper representation, one-time display, lookup, revocation, and shared-key ownership.
- Request size and runtime type validation, rate/concurrency limits, provider timeout/failure handling, stream parsing, and private-reasoning filtering.
- Outbound URL/configuration trust, redirects, SSRF, and the public OpenCode configuration download. User headers/query parameters must not redirect clients' credentials to another service.
- Secret/token/prompt handling in logs, error messages, traces, browser bundles, test fixtures, local configuration, and version control.

### Supabase, grants, and immutable finances

- PostgreSQL RLS and grants for `anon`, `authenticated`, and `service_role`; SECURITY DEFINER search paths and execute privileges; caller ownership checks; constraint enforcement and race behavior.
- Hackathon campaign eligibility, first-claim attribution, uniqueness, atomic grant/key/wallet creation, retries, and disabled/revoked grants.
- Stripe signature verification, paid-event validation, package/currency checks, retry/idempotency behavior, and wallet targeting. A Checkout redirect is not a payment.
- Reservation creation, actual-usage settlement, release records, concurrent spends, and immutable ledger history.

## Financial invariants to preserve and test

1. Each campaign + Team ID receives at most one $100 grant and one shared promotional spending key.
2. A promotional key spends only its grant wallet; personal paid keys spend only their owner's paid wallet.
3. Promotional usage is charged at reference price. Paid usage retains the configured 40% discount. Apply the existing rounding order; multiplying already-rounded reference cents is not an equivalent oracle.
4. Charges use actual provider input/output/cached usage, including reasoning tokens exactly once. Effort labels are not a price schedule.
5. Wallet balances cannot become negative under concurrent admission/settlement. Replayed requests/payments do not duplicate financial effects.
6. Successful settlement consumes its hold and writes matching usage/debit records atomically. Known pre-inference rejections release holds through the existing audit path.
7. Uncertain outcomes retain holds for reconciliation. Never release a hold merely because it is old or to make a verification report look successful.

Reuse the existing wallet, reservation, usage, Stripe, and API-key architecture. Do not introduce a second financial system or weaken authentication, RLS, signatures, or ownership validation to make tests pass.

## Evidence, verification, and delivery

- Cite file paths and lines, trace attacker-controlled input to the sensitive operation, and distinguish confirmed defects from hypotheses and deployment questions.
- Use local fixtures and the existing isolated-schema database tests. Do not spend production credit, mint real grants, send unsolicited messages, or change live security settings merely to demonstrate a hypothesis.
- Never print or copy whole `.env` files, test credential state, access/refresh tokens, API keys, or credential-bearing database URLs. Inspect presence/structure and report redacted evidence.
- Use `npm audit` / Python dependency advisory tools where available; report exact affected versions and distinguish production dependencies from tooling. Do not execute arbitrary downloaded install scripts or send private source/secrets to an external scanner.
- Put findings in `docs/security-review.md` with severity, impact, prerequisites, evidence, proposed fix, verification, and unresolved assumptions. If producing a full threat model, follow the threat-model skill's output contract too.
- If fixes were requested, implement confirmed findings in small changes and run relevant regression checks. For auth changes, include browser/PKCE/account tests; for money changes, include PostgreSQL concurrency/idempotency/isolation tests.
- Report exactly what was tested and what remains unverified. Passing ordinary tests alone is not proof of security.
