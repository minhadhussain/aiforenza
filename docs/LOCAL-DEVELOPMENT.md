# Local development and runtime verification

From the repository root, run `npm run dev`.

The launcher (`tools/dev.py`) checks required backend Supabase settings and the
frontend API URL, refuses occupied dev ports, starts the existing Docker Redis
service, checks Redis PING, and launches exactly one local app stack:

- Frontend: http://127.0.0.1:3000
- API: http://127.0.0.1:8000/v1
- Redis: Docker Compose, port 6379

Docker Desktop must already be running. Python app dependencies and npm
dependencies must already be installed. No packages are installed by the launcher.
Ctrl+C stops the launched app process trees; Redis is left running. If an app
process exits, its companion is stopped rather than leaving a half-running stack.
Do not run a second `next dev` on port 3001 against the same `.next-dev` directory.
Do not delete build output while a Next process is running.

## Configuration

Backend settings load the repository root `.env` by a path relative to source,
not the terminal working directory. The dev launcher also passes the absolute
file to Uvicorn. Container layouts use `/app/.env` if present, with injected
environment variables retaining priority. Existing secrets are never generated
or replaced automatically. In particular, changing an API-key pepper would
invalidate existing keys and is not part of this fix.

Next loads `apps/web/.env.local`. Its local API base must be
`http://127.0.0.1:8000/v1` or `http://localhost:8000/v1`, not temporary port 8001.
The frontend `dev` script explicitly chooses port 3000 rather than automatically
falling back to 3001. CORS allows the configured localhost/127.0.0.1 equivalent
origin without widening access to arbitrary hosts.

## Repeated Supabase runtime error

The incident was reproduced with a real authenticated session: both stale APIs
on 8000 and 8001 returned `SUPABASE_URL is not configured.` despite fresh Python
processes loading the correct settings. Old Uvicorn reload workers survived
partial process termination. Two Next servers also shared the same dev output.
All confirmed old app trees and the orphaned worker were stopped before starting
the new coordinated stack. Health 200 and unauthenticated redirects did not prove
the dashboard worked and must not be used as substitutes for authenticated tests.

`python tools/verify_dashboard_runtime.py` signs in to the existing local test
identity, checks authenticated usage/key/overview endpoints, and checks rendered
dashboard, usage, and API-key pages. `--keys` additionally creates, lists and
revokes one temporary key through normal authenticated API endpoints, including
CORS preflight checks. It never makes an inference request or alters holds.
Test login state is read programmatically from the Git-ignored
`tools/.opencode-test.env.local`; do not print or commit that file.

Verified after repair: usage, key listing and overview HTTP 200; temporary key
creation HTTP 201 with CORS headers and successful revocation; authenticated
dashboard HTTP 200 showing $4.98. Only 3000, 8000 and Docker Redis 6379 remain
listening. Historical reservations and payment/provider configuration were not
changed.
