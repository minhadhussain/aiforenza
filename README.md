# AI Model API Credit Platform

This repository contains the MVP foundation for a prepaid, OpenAI-compatible AI model API platform.

## Current Status

Phase 1 through Phase 10 foundations are in place:

- monorepo structure
- Next.js web foundation
- FastAPI API foundation
- Docker and Docker Compose scaffolding
- environment variable template
- Redis, LiteLLM, and Caddy infrastructure wiring
- Supabase auth client utilities and protected dashboard scaffolding
- backend token validation wiring for dashboard APIs
- wallet and transaction schema with idempotent signup credit bootstrapping
- dashboard overview backed by wallet and transaction data
- API key schema, hashing flow, dashboard management, and auth dependency wiring
- model catalog schema, `/v1/models`, and LiteLLM-backed chat completion forwarding
- usage records, customer pricing fields, and atomic wallet charge foundations
- Stripe Checkout session creation, webhook-driven wallet crediting, and top-up history foundations
- dedicated dashboard views for usage, transactions, models, API keys, balance, and top-ups
- backend observability hooks, basic Redis-backed rate limiting, and production runbook foundations

## Repository Layout

- `apps/web` - Next.js dashboard and marketing site
- `apps/api` - FastAPI application and tests
- `packages/shared` - shared package workspace placeholder
- `infra/caddy` - reverse proxy configuration
- `infra/docker` - infrastructure support files
- `doc` - project planning and build documentation

## Quick Start

1. Copy `.env.example` to `.env`
2. Fill in Supabase, Stripe, Azure, and monitoring values
3. Start services with `docker compose up --build`
4. Open `http://localhost:3000` for the web app
5. Open `http://localhost:8000/docs` for the API docs

## Authentication Foundation

- Web auth uses Supabase browser, server, and middleware clients.
- `/login` and `/signup` provide the initial account entry flow.
- `/dashboard` is protected through server checks and middleware refresh.
- Backend dashboard APIs validate Supabase bearer tokens before returning user data.

## Notes

- Money and billing logic should use integer cents only.
- LiteLLM handles provider normalization, not business logic.
- Supabase, Stripe, and Azure remain external services.

## Local Stripe Development

Use Stripe test mode only for local development.

1. Make sure `STRIPE_SECRET_KEY=sk_test_...` is present in `.env`
2. Start the backend:
   - `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file .env`
3. Install and authenticate the Stripe CLI:
   - `stripe login`
4. Start webhook forwarding:
   - `stripe listen --forward-to localhost:8000/v1/webhooks/stripe`
5. Stripe CLI will print a signing secret like:
   - `whsec_...`
6. Put that value into:
   - `STRIPE_WEBHOOK_SECRET=whsec_...`
7. Restart the backend so it loads the new webhook secret.
8. Start the frontend:
   - `npm --workspace apps/web run dev`
9. Log in, open `/dashboard/billing`, choose a top-up amount, and complete a Stripe test payment.
10. Stripe CLI forwards `checkout.session.completed` to `http://localhost:8000/v1/webhooks/stripe`.
11. The backend verifies the Stripe signature, processes the topup once, credits the wallet, and records the transaction.

Important notes:

- The frontend redirect does not credit the wallet.
- The backend credits the wallet only after verified webhook processing.
- The local webhook secret comes from Stripe CLI, not a production dashboard endpoint.
- Stripe Checkout is created in INR for domestic payments, while the AI Forenza wallet remains USD.
- The INR amount is derived on the backend from the configured Frankfurter USD/INR quote source and cached server-side.
