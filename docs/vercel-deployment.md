# Deploy the frontend and API to Vercel

Create **two Vercel projects from this Git repository**. Each app has its own `vercel.json`; the API uses Vercel's native FastAPI runtime. Supabase and Redis are hosted external services.

| Setting | Frontend project | API project |
| --- | --- | --- |
| Root Directory | `apps/web` | `apps/api` |
| Framework Preset | Next.js | FastAPI |
| Runtime | Node.js 22.x | Python 3.12 |
| Install | `npm ci` from the monorepo workspace | Automatic from `pyproject.toml` / `uv.lock` |
| Build | `npm run build` | Automatic FastAPI build |
| Output | `.next` | Native Vercel Function |
| Entrypoint | Next.js App Router | `app.main:app` |

For the frontend, enable **Include source files outside of the Root Directory in the Build Step**, so Vercel can use the root npm lockfile and shared workspace. Keep the API project scoped to `apps/api`.

## 1. Prepare hosted dependencies

- Use the Supabase project with the repository's migrations applied.
- Provision a Redis instance reachable from Vercel. Supply its **TCP Redis URL**, normally `rediss://...`, as `REDIS_URL`; an Upstash REST URL/token is not a Redis TCP connection string. The existing atomic rate/concurrency checks require Redis and fail closed when it is unavailable.
- Use the configured Azure endpoint/key directly, or an independently hosted authenticated LiteLLM endpoint. The local Compose services and `redis`/`litellm` Docker hostnames are not available in a Vercel Function.
- Select a Vercel function region near Supabase and Redis in the project settings.

## 2. Configure the API project

Import the repo with Root Directory **`apps/api`** and set these Vercel environment variables before deploying:

| Variable | Value |
| --- | --- |
| `API_ENV` | `production` |
| `SUPABASE_URL` | Hosted Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase public anon key used for session verification |
| `SUPABASE_SERVICE_ROLE_KEY` | Private service-role key; API project only |
| `API_KEY_PEPPER` | Existing private pepper; preserve it to keep issued keys valid |
| `REDIS_URL` | Hosted Redis TLS connection URL |
| `AZURE_ENDPOINT` | Configured HTTPS endpoint ending in `/openai/v1` |
| `AZURE_API_KEY` | Private provider credential; API project only |
| `NEXT_PUBLIC_API_BASE_URL` | Public API domain, e.g. `https://your-api.vercel.app/v1` |
| `NEXT_PUBLIC_APP_URL` | Frontend domain, e.g. `https://your-web.vercel.app` |
| `API_CORS_ORIGINS` | Exact frontend origin(s), comma-separated; no trailing slash |
| `STRIPE_SECRET_KEY` | Server-side Stripe key for the intended environment |
| `STRIPE_WEBHOOK_SECRET` | Signing secret for this deployment's Stripe webhook |

Optional settings include existing rate limits, observability settings, and `API_REQUEST_TIMEOUT_SECONDS`. The public URL variables contain URLs, not credentials. `DATABASE_URL` is only required for organizer/migration tools; normal request handling uses Supabase's API.

After the initial import assigns a domain, update the URL values and redeploy if necessary. A stable custom API domain is preferable for issued keys and downloaded client configurations.

The native FastAPI entrypoint preserves the existing paths:

- `https://your-api.vercel.app/healthz`
- `https://your-api.vercel.app/docs`
- `https://your-api.vercel.app/v1/models`
- `https://your-api.vercel.app/v1/chat/completions`
- `https://your-api.vercel.app/v1/hackathon/claim`
- `https://your-api.vercel.app/v1/webhooks/stripe`

There is no additional `/api` prefix. Production API endpoints must be reachable by browsers, API clients, and Stripe without Vercel's interactive deployment-login page; application bearer authentication and webhook signature validation still apply. Configure production Deployment Protection accordingly, while retaining protection on preview environments as appropriate.

## 3. Configure the frontend project

Import the same repo again with Root Directory **`apps/web`**. Set only the frontend's public configuration:

```dotenv
NEXT_PUBLIC_APP_URL=https://your-web.vercel.app
NEXT_PUBLIC_API_BASE_URL=https://your-api.vercel.app/v1
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=YOUR_PUBLIC_ANON_KEY
```

Leave `API_INTERNAL_BASE_URL` unset on Vercel, or set it to the same reachable HTTPS API URL if needed for server-side requests. Never use the Docker-only `http://api:8000/v1` value here. Provider, Stripe-secret, service-role, and database credentials belong only in the API project.

Vercel automatically sets `VERCEL=1`; the Next.js configuration then uses Vercel's normal output rather than the Docker standalone server. Public `NEXT_PUBLIC_*` values are embedded at build time, so redeploy after changing them.

## 4. Connect authentication and payments

- In Supabase Auth, set the production Site URL to the frontend domain and allow `https://your-web.vercel.app/auth/callback**`. Add the corresponding custom-domain callback when used. Keep email confirmation enabled.
- Google's OAuth redirect remains Supabase's `https://your-project.supabase.co/auth/v1/callback`, not the frontend or API domain.
- Register `https://your-api.vercel.app/v1/webhooks/stripe` in Stripe for `checkout.session.completed` and `checkout.session.async_payment_succeeded`, then save that endpoint's signing secret in the API project.
- Set separate Preview environment values, including the matching API URL, CORS origin, Supabase callback, and Stripe test settings. Do not connect disposable previews to production credit/payment data.

## 5. Team-credit billing

Organizer-issued Team IDs create `PROMOTIONAL` keys and a separate project wallet. These keys always use **100% of the reference rate**, including cached-input and output rates. For example, a request with a $1.00 reference cost deducts **$1.00** from the team's credits; the normal 40% paid-key discount does not apply.

The authenticated API key determines the billing source. A request body cannot request a paid discount, select another wallet, or change the charged amount. Preflight reservations, non-streaming settlement, and streaming settlement use the same policy. Promotional credit never falls back to a personal paid wallet.

Follow [organizer setup](hackathon-credits.md#deployment-and-organizer-setup) to enable a campaign and its eligible Team IDs. Run organizer/migration commands from a controlled environment using the private database configuration, not from a public endpoint.

## Function duration and streaming

The committed API function uses Fluid compute and a **300-second maximum duration**, compatible with Hobby's documented maximum. On Vercel, the app defaults to a **240-second execution deadline**, allowing cleanup before the platform limit. It returns a 504 before headers, or an SSE `request_timeout` error after streaming starts. It does not emit a successful `[DONE]` or release financial holds when inference may already have started.

For longer requests on a plan supporting 800 seconds, change `functions["app/main.py"].maxDuration` to `800` and set `API_REQUEST_TIMEOUT_SECONDS=750`. Keep the application deadline below the platform maximum. Client timeout settings cannot extend Vercel's function limit. The provider transport also retains its existing connect/read timeouts.

Normal cancellation closes the upstream stream and releases its concurrency slot. A hard process termination can still leave uncertain holds or stale concurrency counters; use the existing reconciliation procedures rather than clearing financial state or flushing Redis.

The API's 1 MB input limit remains below Vercel's documented 4.5 MB request/response limit. Python bundles exclude tests, caches, and environment files. Native FastAPI lifespan and `StreamingResponse` support are used directly.

## Verify the deployment

```bash
curl --fail https://your-api.vercel.app/healthz
curl --fail https://your-api.vercel.app/v1/public/opencode-config
```

Then verify Google/email sign-in, the dashboard, credit claiming with a dedicated organizer test code, model discovery using that project's key, and a bounded request. Check that the request's billing source is `PROMOTIONAL`, charged cents equal reference cents, savings are zero, and the personal wallet did not change. A health response alone does not validate Redis, credentials, billing, or provider inference.

Repository checks:

```bash
uv run --project apps/api --python 3.12 --extra dev python -m pytest apps/api/tests/test_hackathon.py apps/api/tests/test_request_deadline.py
npm --workspace apps/web run build
```

## Repository verification status

Verified locally with the Python 3.12 locked environment: 408 backend tests passed (15 opt-in database/Redis tests skipped), including full-price team billing, both response modes, and deadline cleanup. The frontend built with `VERCEL=1`, its 18 auth tests passed, both JSON configurations validated against Vercel's published schema, and the configured ASGI entrypoint passed health/auth/CORS checks.

The opt-in PostgreSQL run was attempted separately but could not connect: the configured Supabase pooler reported `tenant/user not found`. Update the private database connection and rerun those checks before launch. The connection fixture now reports failures without dumping the credential-bearing DSN. No hosted Vercel deployment was created during these checks.

## Official references

- [FastAPI on Vercel](https://vercel.com/docs/frameworks/backend/fastapi)
- [Monorepo project roots](https://vercel.com/docs/monorepos)
- [Python versions and dependency manifests](https://vercel.com/docs/functions/runtimes/python)
- [Function duration, bundle, and payload limits](https://vercel.com/docs/functions/limitations)
