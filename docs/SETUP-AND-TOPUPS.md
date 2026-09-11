# Exact setup, OpenCode and top-up steps

## 1. Prepare the development environment

Use Python 3.11+, Node.js supported by Next 15.4, npm, Docker Desktop and Stripe CLI.
Open terminals in the repository root (`D:\aiforenza` on this workstation).

```powershell
npm ci
python -m pip install -e "apps/api[dev]"
```

For optional browser/database verification:

```powershell
python -m pip install playwright psycopg2-binary
python -m playwright install chromium
```

Do not overwrite existing `.env` files. If starting from a fresh clone, copy the
root `.env.example` to `.env`, then configure the following privately:

| File | Required settings |
| --- | --- |
| Root `.env` | `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `REDIS_URL=redis://127.0.0.1:6379/0`, `AZURE_ENDPOINT`, `AZURE_API_KEY` |
| Root `.env` for test payments | `API_ENV=development`, `STRIPE_SECRET_KEY=sk_test_...`, `STRIPE_WEBHOOK_SECRET=whsec_...`, `STRIPE_DOMESTIC_CURRENCY=inr`, `STRIPE_FX_RATE_API_URL=https://api.frankfurter.dev/v2/rate/USD/INR`, `NEXT_PUBLIC_APP_URL=http://127.0.0.1:3000` |
| `apps/web/.env.local` | `NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000/v1`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` |

`DATABASE_URL` is required for opt-in database integration tests, not browser use.
Preserve any existing `API_KEY_PEPPER`; changing it invalidates key hashes.
Never put Stripe, Azure or Supabase service-role credentials in frontend variables.
Configure Supabase Auth's site/redirect URLs for the actual browser origin. Use
one origin consistently: localhost and 127.0.0.1 have different browser cookies.

## 2. Apply database migrations

Follow [SUPABASE-SETUP.md](SUPABASE-SETUP.md). The canonical migrations are in
`supabase/migrations/`, not the older `infra/supabase` snapshots. Verify the target
project and migration history before applying changes. Do not reset a shared DB.

## 3. Start the application

1. Start Docker Desktop and wait until its engine is running.
2. In terminal A, run:

```powershell
npm run dev
```

3. Wait for Next to be ready and Uvicorn application startup to complete.
4. Open `http://127.0.0.1:3000`. API docs: `http://127.0.0.1:8000/docs`.
5. If the launcher says a port is occupied, reuse or stop that existing dev stack.
   Do not start another Next instance on 3001 or an API on 8001.

## 4. Start Stripe webhook forwarding BEFORE paying

Install/login to the Stripe CLI against the same **test account** as the backend.
This repository's local Windows executable is `tools/stripe/stripe.exe`; it is
ignored by Git and must be installed separately on a fresh clone. The helper also
supports `stripe` installed on PATH.

First-time setup, in a private terminal:

```powershell
stripe login
stripe listen --events checkout.session.completed,checkout.session.async_payment_succeeded --forward-to http://127.0.0.1:8000/v1/webhooks/stripe
```

Copy the listener's signing secret privately into root `STRIPE_WEBHOOK_SECRET`,
stop the first listener, and restart terminal A so FastAPI loads the value.
The CLI account must match `STRIPE_SECRET_KEY`. Do not publish the signing secret.

For routine local testing, terminal B:

```powershell
npm run dev:payments
```

This helper uses the backend's test key without putting it on the command line,
checks that the signing secret matches, redacts secrets, and forwards to the real
webhook route. Keep it running. A mismatch stops startup and requires correcting
the secret/restarting the API. Do not run two listeners unnecessarily.

## 5. Sign in and configure the correct API key

1. Sign up, verify email if required by Supabase, then log in.
2. Confirm the dashboard account identity and the one-time $5 trial credit.
3. Open `/dashboard/api-keys`, create a key, copy it once into a secret manager.
4. Confirm the same account is selected when adding funds. A separate test account
   and your personal account have different balances even on the same computer.
5. Merge `docs/opencode.example.json` into `~/.config/opencode/opencode.json` for
   user-wide access (Windows: `%USERPROFILE%\.config\opencode\opencode.json`).
   Preserve existing providers/defaults. A project `opencode.json` is an alternative
   for that project only; a Desktop config is not used from unrelated repositories.
6. Set `AI_FORENZA_API_KEY` privately in the terminal environment to that key.
7. Start/restart OpenCode and choose `aiforenza/gpt-5.4`:

```powershell
opencode run --model aiforenza/gpt-5.4 "Reply briefly: hi"
```

Never use the Azure key here. Project config can override global config; an old
literal `apiKey` can override the key you intended to use. Do not print full
`opencode debug config` output when it contains secrets.

The same API key accesses every enabled model. **Do not select or activate a model
in the dashboard first.** Choose it only inside OpenCode (`/models`) or set the
`model` field on each API request. No new key is required to switch models.

The template lists GPT-5.4, GPT-5.6 Sol, GPT-6 Astra and Grok 4.6. After restarting
OpenCode use `/models` to switch. Preserve Astra's `reasoningEffort: "none"`
setting for tool compatibility. See [MODEL-CHOOSER.md](MODEL-CHOOSER.md).

OpenCode includes system prompts/tools and an output allowance even for “hi”.
A 32,000-token GPT-5.4 allowance needed about $0.36 upfront in this environment;
the actual debit was much smaller. This is not a fixed price for every request.

## 6. Complete a top-up and confirm the money appears

1. Keep both terminal A and terminal B running.
2. On the **API key owner's** `/dashboard/billing`, select $10 and click Add $10.
3. The API creates a PENDING top-up plus a Stripe Checkout URL. This is **not** a
   completed payment and does not add wallet funds.
4. Open the returned URL if using `POST /v1/billing/create-checkout-session` directly.
   That endpoint uses a **dashboard session bearer token**, not an AI Forenza key.
5. In Stripe **test mode only**, use the Indian Visa test card `4000003560000008`,
   a future expiry such as `12/34`, CVC `123`, and test billing details. Complete
   Stripe's test 3DS challenge. Never enter real card details for this test.
6. Confirm Stripe says paid and terminal B shows the session-completed event with
   **HTTP 200** from `/v1/webhooks/stripe`.
7. Return to billing. It polls for up to roughly 60 seconds and shows
   **Payment verified. $10.00 has been added** only for a completed matching top-up.
8. Check `COMPLETED`, one `TOPUP +$10.00` transaction, total balance increased by
   $10.00, and the available balance after subtracting existing holds.
9. Use **Refresh balance and top-ups** if needed. Do not pay again merely to refresh.
10. Continue using the existing key; no key regeneration is needed after top-up.

The verified run collected **₹950.90** for **$10.00 credit**. Future INR amounts
depend on the live server FX quote; do not hard-code this exchange rate.

## 7. If funds do not show

| Observation | Action |
| --- | --- |
| Stripe session open/unpaid | Complete Checkout and 3DS; creating a URL alone is not payment. |
| Stripe paid, app PENDING | Check webhook forwarding, correct account/secret, backend logs and HTTP status. Replay the original event after fixing delivery. |
| Webhook 400 | Investigate signature, mode, ownership, amount and currency mismatch; never bypass validation. |
| Webhook 503 | Check required settings, migrations and database access, then replay. |
| Top-up COMPLETED but wrong account balance | Compare the signed-in account with the API key owner; funds never transfer across accounts automatically. |
| Total rose but available is lower | Inspect outstanding reservations; do not delete uncertain holds. |
| Browser return asks for login | Sign in on the configured return origin; cookie origins differ. Payment credit is independent of this redirect. |

Operator replay, after verifying the correct Stripe account and the original event:

```powershell
stripe events resend evt_REPLACE_WITH_VERIFIED_EVENT_ID
```

In production, resend to the registered endpoint with `--webhook-endpoint we_...`.
The same event/session must produce no second credit. `stripe trigger` creates
generic fixtures and is not proof that an app-created top-up has been paid.
Never fabricate a signed “paid” event or manually increase balances to pass a test.

## 8. Verification commands

Open a terminal in `apps/api`:

```powershell
python -m pytest -q --tb=short
$env:RUN_DATABASE_TESTS="1"
$env:RUN_REDIS_TESTS="1"
python -m pytest -q --tb=short
```

Run these pytest commands from `apps/api`. PostgreSQL tests create/drop only a random isolated schema.
Do not run load tests against Stripe's sandbox API.

`python tools/verify_dashboard_runtime.py` verifies the locally configured test
identity without inference. `--keys` creates then revokes a temporary test key.
The incident-specific payment harness (`tools/verify_payments_e2e.py`) uses that
private test identity and recorded state; see its command help. `prepare`,
`browser`, and `api` have side effects and must not be repeatedly invoked just to
check status. Use `audit`, `browser_verify` and the report for repeat checks.
