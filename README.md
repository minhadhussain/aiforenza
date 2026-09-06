# AI Model API Credit Platform

This repository contains the MVP foundation for a prepaid, OpenAI-compatible AI model API platform.

## Current Status

Phase 1 is in place:

- monorepo structure
- Next.js web foundation
- FastAPI API foundation
- Docker and Docker Compose scaffolding
- environment variable template
- Redis, LiteLLM, and Caddy infrastructure wiring

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

## Notes

- Money and billing logic should use integer cents only.
- LiteLLM handles provider normalization, not business logic.
- Supabase, Stripe, and Azure remain external services.
