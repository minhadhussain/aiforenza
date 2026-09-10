# OpenCode balance-check investigation

## Verified cause

The key in the user's local OpenCode project configuration was matched by its
hash to the existing AI Forenza key and wallet. No replacement test account or
test key was used to diagnose this incident.

Before verification:
- Wallet total: 493 USD cents.
- 14 open request reservations: 480 USD cents.
- Spendable balance: 13 USD cents.
- The dashboard incorrectly labeled the total as AVAILABLE BALANCE.

The saved OpenCode request uses `gpt-5.4`, 32,000 maximum output tokens,
two messages and ten tools. Its existing conservative input budget is 43,712
tokens (UTF-8 serialized bytes plus overhead), not actual billed input usage.
The existing pricing calculation gives a 59-cent maximum reference charge and
a 36-cent maximum discounted customer charge. It cannot fit in 13 available cents.
The direct PowerShell-style request used only 16 output tokens and required a
one-cent reservation. These were different requests, not contradictory decisions.

OpenCode logs contain provider 502 failures followed by 402 rejections. The old
request-finally block released Redis concurrency slots, but never released a
PostgreSQL hold for a definitive no-inference provider rejection. Repeated failed
attempts therefore reduced available capacity without reducing displayed cash.

## Changes

- `wallet_availability` returns total, reserved and available USD cents in one
  PostgreSQL snapshot. Both dashboard and access checks use it.
- `reserve_usage` remains the final atomic row-lock check. No Redis wallet cache,
  reference-price comparison, INR conversion or frontend authorization is used.
- Overview and billing distinguish available funds from total wallet cash.
- Confirmed provider HTTP 400/401/403/404/422/429 rejections and connection/pool
  failures before a request can be delivered release only that request's hold.
- Releases are audited, owner-scoped, idempotent and do not create wallet credits.
- Post-provider billing failures, read timeouts, interrupted streams and 5xx errors
  retain reservations until consumption can be reconciled. They are not silently
  released on age alone.
- Safe structured diagnostics include request/user/key IDs, wallet ID/currency,
  total/reserved/available cents, input estimate, output limit, reference/customer
  maximum charges, model and comparison result. No credentials or prompts.

The 40% discount implementation, Stripe, FX, Azure gateway, model mapping and
output allowance have not been changed by this fix.

## Tests and actual-account result

`tests/test_balance_decisions.py` covers $10 small/normal tool requests, zero,
one-cent underfunding, $1 reference cost / $0.60 customer cost at both $1 and
$0.50 balances, identical client decisions, safe failure classification and
route cleanup. The PostgreSQL integration test exercises competing reservations,
availability snapshots, exact balance, idempotent settlement, audited release,
wrong-owner rejection and refusal to release settled usage.

`tools/verify_opencode_balance.py` uses the existing OpenCode key locally:
- Small real request: HTTP 200, actual response received, one-cent debit.
- Saved OpenCode request: HTTP 402, maximum customer charge 36 cents versus
  12 cents remaining available after the small test.
- Total afterward: 492 cents. Reserved remains 480 cents. No new leaked holds.

## Remaining incident reconciliation

The historical 14 holds still require provider/request outcome evidence. The
saved generic 502 error alone is not sufficient to prove zero consumption.
No historical holds were deleted, no wallet funds added, and no uncertain usage
written off during this fix. The original OpenCode request is therefore still
correctly blocked on this account until enough holds are reconciled or it has
enough available funds. Do not describe this as a successful live OpenCode run.

To reconcile, correlate each held request ID with authoritative provider outcome
or internal no-inference error evidence; release only confirmed unconsumed holds
through the owner-scoped RPC. Requests with actual usage require settlement;
uncertain outcomes need explicit operator review. Do not bulk-delete holds.

## Historical audit follow-up

The read-only audit was run against the same configured OpenCode key. It scanned
141 backend/OpenCode log and storage files and the local SQLite `message` and
`part` tables. Database references also include later investigation transcripts;
these are not independent evidence of the original provider outcome. Repeated
references are deduplicated in the audit report.

No matching usage record or `usage:<request_id>` ledger transaction was found for
any of the 14 holds. Only the last two have structured original client-log
responses, both downstream HTTP 502 / `provider_unavailable`, without usage.
This does not establish the upstream status or prove zero consumption.

| Request ID | Held USD cents | Decision |
| --- | ---: | --- |
| `req_54aba23b8d2143a6b24530c152a6d408` | 36 | Retain: no authoritative outcome |
| `req_cca2487ec37e45fc8972439ef12b6414` | 30 | Retain: no authoritative outcome |
| `req_3842232cb25d4d5c86f1ed909762b748` | 30 | Retain: no authoritative outcome |
| `req_05418154567f470faf16638ab7f9813e` | 36 | Retain: no authoritative outcome |
| `req_d475669a8d8a4386a38bbdc1f08b9727` | 30 | Retain: no authoritative outcome |
| `req_296045e2d4744c87863e266d41fbeac9` | 36 | Retain: no authoritative outcome |
| `req_67e468c1c8634d1fa09fbe69fb267770` | 36 | Retain: no authoritative outcome |
| `req_f6b8041b20d8446bab07fcc9fb2903e8` | 36 | Retain: no authoritative outcome |
| `req_afa0ab33539b42e8a2005943becbc96e` | 36 | Retain: no authoritative outcome |
| `req_2f7664432ef74e419d4531da6722f35d` | 36 | Retain: no authoritative outcome |
| `req_54c0ec32468f4f29b7af2d00efa3414a` | 36 | Retain: no authoritative outcome |
| `req_7164f5e3011d422fbd25f4a8e6a66b19` | 36 | Retain: no authoritative outcome |
| `req_c6ef985b121e4d99b13f66957b1a1a24` | 30 | Retain: generic downstream 502 only |
| `req_5f905c63ec874b15b0427a96f229bb8c` | 36 | Retain: generic downstream 502 only |

Released: **0**. Settled: **0**. Final cash total: **492 cents**; reserved:
**480 cents**; available: **12 cents**. No inference request was made during this
follow-up, no wallet credit was created, and no reservation was deleted.
Actual OpenCode success remains unverified: the saved normal request needs a
36-cent reservation and cannot fit in 12 available cents.

### Evidence needed to unblock reconciliation

Obtain a sanitized provider/gateway diagnostic export for **2026-09-09
21:09:40–21:21:00 UTC**, including request correlation, upstream response status,
terminal outcome, and authoritative input/output/cached token usage where present.
The gateway does not currently forward the internal `req_...` ID in its headers;
provider records therefore need a trustworthy mapping back to each local request.
Timestamp proximity or aggregate token charts alone are insufficient.

Azure Monitor Log Analytics requires Microsoft Entra authentication and workspace
read permissions; an inference API key is not sufficient. Resource logs are only
available if diagnostic collection/routing was configured when requests occurred.
Enabling it now does not recover missing historical outcomes. No Azure settings
were changed during this investigation.

References checked:
- [Azure OpenAI monitoring](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/monitor-openai)
- [Diagnostic settings](https://learn.microsoft.com/en-us/azure/azure-monitor/platform/diagnostic-settings)
- [Log Analytics authentication](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/api/access-api)

### Follow-up verification

The full backend suite initially passed with **106 passed, 3 skipped**. Opting in
to PostgreSQL tests produced **30 passed, 1 failed**: the wallet concurrency,
release and settlement test passed, while the separate top-up fixture failed
because it omits the live schema's required `package_id`. This is not a successful
top-up integration result and payment behavior was not changed to hide it.
Database URL fixture representations are now redacted to prevent pytest argument
displays from printing credentials. The credential exposed in the earlier failure
output should be rotated through the operator's normal secret-management process.

Final reruns after redaction: **107 passed, 3 skipped** in the full backend suite;
**31 passed** in the wallet-only PostgreSQL, balance-decision and audit tests.
`git diff --check` passed. The unrelated opt-in top-up fixture failure remains
unresolved and was excluded explicitly from the wallet-only rerun.
