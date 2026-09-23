---
description: Review AI Forenza authentication, API keys, Supabase, and financial security using the installed skills
agent: build
---

Load the `aiforenza-security-review` skill and follow it for this repository.

Perform an evidence-based system security review covering the browser/auth boundary, FastAPI endpoints, Supabase RLS/privileged RPCs, API keys, Stripe, hackathon grants, reservations, usage/ledger, model gateway, and OpenCode configuration. Use the downloaded specialist skills when relevant.

Write an actionable report to `docs/security-review.md`. Distinguish confirmed defects, existing protections, deployment assumptions, and unverified hypotheses. Keep secrets and user prompts out of reports and logs. Use the existing architecture and tests.

By default this command requests a review/report. If the user's additional instructions request implementation, also make focused fixes to confirmed issues and run the corresponding regression tests.

Additional user instructions:
$ARGUMENTS
