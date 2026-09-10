# Real OpenCode verification with an isolated trial wallet

> This records the initial test-account checkpoint. Later, with user approval,
> the desktop OpenCode config was switched to this account and successfully
> tested again (498 → 496 cents). It is no longer the one-request fixture below.
> Latest top-up and API balances: [FINAL-E2E-2026-09-10.md](FINAL-E2E-2026-09-10.md).
> Use `verify_dashboard_runtime.py` for current read-only runtime checks rather
> than the original one-request assertions. The top-up test fixture issue is fixed.

## Result

OpenCode **1.2.27** successfully called `gpt-5.4` through
`http://localhost:8000/v1` with a newly generated AI Forenza key.
The CLI exited **0**, emitted `step_start`, `text`, `step_finish`, and finished
with `stop`. No mock provider or direct replacement request was used.

- User: `3b229039-478e-48c9-9152-8eef348288ae`
- API key ID: `c3cddda7-d907-4191-82bb-a4b8129d1c86` (plaintext never printed)
- Request: `req_46f013d7332c4fe5985fc4f8282aead4`
- Wallet: `f0286105-df88-4d0a-b674-fc6404d556da`

The synthetic user was created and email-confirmed through the Supabase Auth
admin endpoint. Trial credit came from the **existing dashboard bootstrap**,
not a manual balance edit: exactly one `FREE_TRIAL +500` ledger transaction.
Calling bootstrap twice did not duplicate the credit. API key creation used
the ordinary authenticated `/v1/api-keys` endpoint.

## Request flow and billing

1. OpenCode custom `@ai-sdk/openai-compatible` provider authenticates to AI Forenza.
2. Preflight estimates 43,890 input tokens and permits 32,000 output tokens.
   Reference maximum: 59 cents; customer hold: **36 cents**.
3. Existing atomic reservation RPC reserves that amount against $5.00 available.
4. The backend calls the configured Azure endpoint. A read-only HTTPX response
   hook records **Azure HTTP 200** correlated to the internal request ID; neither
   endpoint, credentials, request content nor response content is logged.
5. Streaming usage: **8,727 input**, **0 cached**, **32 output** tokens.
6. Exactly one completed usage record and one matching `USAGE -2` ledger entry
   are persisted; the reservation is removed by normal settlement.
7. OpenCode receives the terminal successful stream and exits normally.

| Amount | USD |
| --- | ---: |
| Wallet before | $5.00 |
| Reference calculation, before rounding | $0.0222975 |
| Customer calculation, reference × 0.60 | $0.0133785 |
| Reference charge, rounded up to cents | $0.03 |
| Customer charge / actual wallet deduction | **$0.02** |
| Recorded savings | **$0.01** |
| Wallet after / available | **$4.98** |
| Remaining reserved | **$0.00** |

The existing 40% discount is applied **before** integer-cent ceiling rounding.
The rounded two-cent debit is therefore not exactly 60% of the rounded three-cent
reference figure; the unrounded customer amount is exactly 60% of reference.

Both `/v1/dashboard/overview` and the authenticated, server-rendered Next.js
`/dashboard` page returned 200 and matched **$4.98 available / $4.98 total /
$0.00 reserved**. This checks rendered HTML, not a screenshot or browser interaction.

## Compatibility blocker fixed

The fresh balance exposed two independent provider-payload problems:

- OpenCode serialized `reasoningSummary`, which Azure's Chat Completions endpoint
  rejected. This Responses-only client option is now omitted at the Chat boundary.
- GPT-5.4 rejected `max_tokens`. It is now translated to `max_completion_tokens`
  with the **same allowance and precedence as preflight**. Other models' token
  parameter behavior is unchanged.

The initial retrying CLI was stopped; subsequent attempts were bounded. Eight
new test requests were rejected by Azure with HTTP 400 and released through the
existing audited no-inference cleanup. They created no usage charges and left no
holds. These results do **not** prove outcomes for any historical request.

## Original account preserved

The original wallet, all 14 historical reservation rows, transaction history and
release-audit rows were fingerprinted before provisioning and compared afterward.
They are unchanged: **492 cents total, 480 reserved, 12 available**.
No historical hold was released or adjusted.

Stripe, Frankfurter, Azure configuration, model prices, the 40% discount, wallet
architecture and historical reservation amounts were not modified.

## Local reuse and verification

- `python tools/opencode_live_test.py connect` launches interactive OpenCode with
  the same fresh test key and isolated configuration; future requests consume
  the remaining test wallet normally.
- `python tools/opencode_live_test.py verify` rechecks the original one-request
  test without making an inference call. Run before further interactive usage;
  it intentionally expects exactly one usage record.
- Private test login/key/session state: `tools/.opencode-test.env.local`.
  This file and `tools/.opencode-test-workspace/` are Git-ignored. Do not share them.
- The existing desktop OpenCode configuration/key was not overwritten.
- Local backend and frontend were started because neither was running. The
  backend verification launcher wraps the real app with observation only.

## Tests and remaining issues

- Full backend suite: **112 passed, 3 skipped**.
- Opt-in PostgreSQL wallet safety and compatibility subset: **27 passed**.
- Targeted Chat/OpenCode/balance regressions: **32 passed**.
- The original account still needs authoritative historical reconciliation.
- Provider 400 failures are still exposed as generic downstream 502 errors,
  which can cause client retries; this test does not redesign error handling.
- The previously discovered unrelated opt-in top-up test fixture issue and
  previously exposed database credential rotation remain separate follow-ups.
- No commit or push was made.

References: [OpenCode CLI](https://opencode.ai/docs/cli/),
[OpenCode config](https://opencode.ai/docs/config/),
[Azure reasoning API parameters](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/reasoning).
