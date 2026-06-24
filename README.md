# HomeStack

A secure, modular, **self-hosted** household management platform for one household,
run on an always-on home server via Docker Compose. It replaces scattered apps with one
warm, family-oriented system: a **Hub** ("what needs attention today?"), a **Calendar**,
opt-in **nodes** (areas of household life), and a touchscreen **kiosk** for the kids.

> **Source of truth:** the canonical docs live in [`docs/`](docs/). Read
> [`HANDOVER.md`](HANDOVER.md) first, then `docs/00_README_and_Changelog.md` (decisions
> D1–D18) and `docs/MILESTONE_1_Checklist.md`. If anything conflicts, the doc set wins.

## Status

Milestone 1 (Walking Skeleton) — **complete**. Milestone 2 (Native Meridian) — **complete**:
the chores/points/rewards node runs natively on shared users, permissions, calendar, Hub
and kiosk, with a dry-runnable data importer. Next: Milestone 3 (Home Wiki, Pets, Education).

## Tech stack

- **Backend:** Python · Django · DRF · PostgreSQL (DRF/apps land in Phase 1.1)
- **Frontend:** React · TypeScript · Vite · TailwindCSS (Tailwind lands in Phase 1.12)
- **Deploy:** Docker Compose on a Linux home server, local-network only
- Redis/Celery and the mobile/desktop client choice are deliberately deferred (D5, D3)

## Repository layout

```
backend/      Django backend (modular monolith)
frontend/     React + TypeScript + Vite app
docs/         Canonical documentation (source of truth)
docker/       Docker support files
scripts/      Backup/restore and data-import (Meridian/Solace) scripts
backups/      Local backup volume target
```

## Getting started (local dev)

Prerequisites: Docker and Docker Compose.

```bash
# 1. Create your env file from the template and edit secrets
cp .env.example .env

# 2. Build and start the three services (postgres, backend, frontend)
docker compose up --build

#    …or with hot-reload bind mounts for development:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Then:

- Backend health: <http://localhost:8000/api/v1/health/> → `{"status": "ok", ...}`
- Frontend: <http://localhost:5173>
- Postgres: `localhost:5432` (healthcheck via `pg_isready`)

Stop with `docker compose down`. Add `-v` to also drop the data volumes.

## Services

| Service              | Port | Notes                                   |
|----------------------|------|-----------------------------------------|
| `homestack-postgres` | 5432 | PostgreSQL 16, `postgres_data` volume   |
| `homestack-backend`  | 8000 | Django; `media_data` + `backup_data`    |
| `homestack-frontend` | 5173 | Vite dev server                         |

## Security note

Local-network only. Do **not** expose HomeStack publicly until the pre-exposure
checklist in `docs/05_Security_Architecture_Document.md` §14 is satisfied
(HTTPS, reverse proxy, rate limiting, strong admin passwords, sensitive-node locking).
