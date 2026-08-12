# HomeStack

A secure, modular, **self-hosted** household management platform for one household. HomeStack
combines a shared Hub, Calendar, People layer and opt-in household domains into one responsive
family-oriented application, with a shared kiosk for child/family use.

> **Start here:** read [`HANDOVER.md`](HANDOVER.md) for the current live state and active work.
> Canonical product/architecture/security documentation lives in [`docs/`](docs/), with settled
> decisions D1–D24 in [`docs/00_README_and_Changelog.md`](docs/00_README_and_Changelog.md).

## Current status

HomeStack is deployed on the home server and is in daily household use.

Current shipped areas include:

- core Hub, Calendar, People, Search, Notifications, permissions, audit and backup/restore;
- Atlas household notes/to-dos plus dedicated Grocery and Shopping surfaces;
- native Meridian tasks/routines/points/rewards/approvals;
- Education, Home Wiki and Pets;
- **Books** with personal Want to Read / Reading / Read shelves, ratings/notes and shared Book Clubs;
- Homestead property/rooms/plans/maintenance/appliances/cover/pools/utilities/floor plan;
- native Solace/Money;
- Fitness & Training (separate from sensitive medical Health, D24);
- Travel trips, booking/cost planning and itinerary/Things to do;
- Corners and safe product/book-link preview/cache/watch flows;
- daily coordination across appointments, Agenda, birthdays and pool schedules;
- **PWA/Web Push notifications** with per-user preferences, per-device subscriptions, quiet hours,
  bundled household activity, scheduled reminders/countdown delivery and sensitive-safe payloads.

Trusted **LAN HTTPS is live** at:

`https://homestack.moosesoftwares.com`

The hostname resolves locally through Pi-hole to the home server; Nginx Proxy Manager terminates a
Let's Encrypt certificate obtained through Cloudflare DNS challenge. This does **not** mean
HomeStack is publicly exposed.

The primary engineering workstream is **production readiness and reliability**. Production serving
is done (v0.35.0); tighter Docker networking, safer deployment automation, frontend/E2E CI and
off-server recovery remain. See [`docs/34_Recommended_Next_Steps.md`](docs/34_Recommended_Next_Steps.md)
and [`docs/04_Development_Roadmap.md`](docs/04_Development_Roadmap.md).

## Tech stack

- **Backend:** Python · Django · Django REST Framework · PostgreSQL
- **Frontend:** React · TypeScript · Vite · TailwindCSS
- **Architecture:** Django modular monolith, API-first, Docker Compose
- **Production serving:** gunicorn (WSGI) · WhiteNoise (Django static) · nginx (built React bundle)
- **Deploy:** Linux home server, LAN-only HTTPS through the existing Nginx Proxy Manager
- **Deferred until justified:** Redis/Celery, durable event broker, native-client technology

## Repository layout

```text
backend/      Django/DRF modular backend
frontend/     React + TypeScript application
docs/         Canonical product/architecture/domain documentation
scripts/      Operational/import/maintenance helpers
brand/        HomeStack brand source assets
backups/      Local backup-volume target
```

## Local development

Prerequisites: Docker and Docker Compose.

`docker-compose.yml` is the **production** stack (gunicorn + a built React bundle on nginx).
Development needs the override, which swaps in `runserver` and the Vite dev server with
bind-mounted source and hot reload:

```bash
cp .env.example .env
# edit local secrets/settings

docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Editing frontend or backend source in development never requires a production image rebuild.

To run the production stack locally exactly as the home server does:

```bash
docker compose up --build
```

Default direct development endpoints:

- backend health: `http://localhost:8000/api/v1/health/`
- frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Updating a running production deployment

The production Compose file builds application source *and build artefacts* — the React bundle and
Django's collected static files — into the images. A plain `git pull` replaces neither.

Typical update sequence — the new image proves itself *before* it replaces the running containers:

```bash
git pull
docker compose build homestack-backend homestack-frontend

# One-off containers from the new image. They do not touch what is currently serving,
# so a non-zero exit here means simply abandon the deploy and fix .env.
docker compose run --rm --no-deps homestack-backend python manage.py check
docker compose run --rm --no-deps homestack-backend python manage.py migrate

docker compose up -d
curl -fsS https://homestack.moosesoftwares.com/api/v1/health/
```

The `check` step runs the production deployment checks and exits non-zero on a misconfigured
`.env`, so do not skip it even when a release adds no migrations.

Full deployment, smoke-test and rollback procedures are in
[`docs/35_Production_Serving_and_Deployment.md`](docs/35_Production_Serving_and_Deployment.md).
Replacing this manual sequence with one supported deployment command is still to come.

## Web Push deployment note

The Web Push implementation is shipped, but the live server needs VAPID configuration and the
scheduled dispatcher. See [`HANDOVER.md`](HANDOVER.md) and
[`docs/32_Core_Notifications_and_Push.md`](docs/32_Core_Notifications_and_Push.md) before deploying
or troubleshooting push.

Do not commit VAPID private keys. On iOS, Web Push must be tested from an installed Home Screen PWA,
not an ordinary Safari tab.

## Production serving

The live stack runs **gunicorn** for Django and serves a **production Vite build from nginx**, with
SPA fallback so deep links survive a refresh, and WhiteNoise serving Django's collected static
files so admin stays styled under `DEBUG=False`. Nginx Proxy Manager keeps terminating TLS and
routing `/api/` to the backend; HomeStack adds no TLS layer of its own.

Container ports are deliberately unchanged. Tightening LAN exposure is the next separate step,
still ahead of any consideration of public access.

## Environment / HTTPS notes

For the current LAN hostname, HomeStack needs the public hostname represented in its environment,
including the allowed-host/CSRF configuration expected by the selected Django settings and:

```text
HOMESTACK_PUBLIC_HOSTNAME=homestack.moosesoftwares.com
```

The **Cloudflare DNS API token does not belong in HomeStack's `.env`** for the current setup. It is
stored in Nginx Proxy Manager's DNS-challenge certificate credentials.

Pi-hole owns the local DNS mapping:

```text
homestack.moosesoftwares.com -> 192.168.1.125
```

Deployment-specific secrets and the real `.env` must never be committed.

## Security

HomeStack is still **LAN-only** by design. Owning a public domain and using a trusted certificate
does not make the instance ready for public internet access.

Before any Cloudflare Tunnel/direct public exposure, satisfy the explicit gate in
[`docs/05_Security_Architecture_Document.md`](docs/05_Security_Architecture_Document.md), including
production serving, stronger adult remote authentication, rate limiting, protected off-server
backups and a dedicated exposure review.

## Documentation maintenance

Use:

- [`HANDOVER.md`](HANDOVER.md) — current state, deployment requirements and what to do next;
- [`docs/00_README_and_Changelog.md`](docs/00_README_and_Changelog.md) — settled decisions and doc map;
- [`docs/01_Master_Software_Specification.md`](docs/01_Master_Software_Specification.md) — product contract;
- [`docs/04_Development_Roadmap.md`](docs/04_Development_Roadmap.md) — current/future sequencing;
- [`docs/05_Security_Architecture_Document.md`](docs/05_Security_Architecture_Document.md) — security contract;
- [`docs/32_Core_Notifications_and_Push.md`](docs/32_Core_Notifications_and_Push.md) — shipped notification/PWA contract;
- [`docs/33_Node_Books.md`](docs/33_Node_Books.md) — Books domain contract;
- [`docs/34_Recommended_Next_Steps.md`](docs/34_Recommended_Next_Steps.md) — practical current execution plan;
- [`docs/35_Production_Serving_and_Deployment.md`](docs/35_Production_Serving_and_Deployment.md) — production serving, deployment, smoke tests and rollback;
- [`VERSION_HISTORY.md`](VERSION_HISTORY.md) — historical release chronology.

Do not turn `HANDOVER.md` back into a permanent implementation diary; Git history and
`VERSION_HISTORY.md` already provide that history.