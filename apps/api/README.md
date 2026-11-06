# API

FastAPI application for the MVP backend.

For Vercel, select this directory (`apps/api`) as the project's Root Directory. The native entrypoint is `app.main:app`, with Python 3.12 selected by `.python-version`. Vercel installs the dependencies declared in `pyproject.toml` and `uv.lock`.

See [Vercel deployment](../../docs/vercel-deployment.md) for hosted Redis/Supabase settings, frontend CORS, authentication callbacks, and the 240-second app / 300-second function deadline.
