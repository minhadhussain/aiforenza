# AI Model API Credit Platform

This repository contains the MVP foundation for a prepaid, OpenAI-compatible AI model API platform.

## Current Status

Phase 1 through Phase 6 foundations are in place:

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
