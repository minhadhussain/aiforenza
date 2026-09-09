# Phase 1 - Foundation

This phase establishes the monorepo and runtime foundation for the MVP.

## Included

- monorepo root structure
- `apps/web` Next.js skeleton
- `apps/api` FastAPI skeleton
- Dockerfiles for web and api
- Docker Compose services for web, api, redis, litellm, and reverse proxy
- Caddy reverse proxy configuration
- `.env.example` for shared environment configuration

## Deferred To Later Phases

- Supabase authentication flows
- wallet and transaction logic
- API keys
- model routing and billing logic
- Stripe webhook processing
- dashboard data views
- developer documentation pages
