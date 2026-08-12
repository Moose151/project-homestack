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
- Homestead property/rooms/plans/maintenance/appliances/cover/pools/utilities/floor plan;
- native Solace/Money;
- Fitness & Training (separate from sensitive medical Health, D24);
- Travel trips, booking/cost planning and itinerary/Things to do;
- Corners and safe product-link preview/cache/watch flows;
- daily coordination across appointments, Agenda, birthdays and pool schedules.

Trusted **LAN HTTPS is live** at:

`https://homestack.moosesoftwares.com`

The hostname resolves locally through Pi-hole to the home server; Nginx Proxy Manager terminates a
Let's Encrypt certificate obtained through Cloudflare DNS challenge. This does **not** mean
HomeStack is publicly exposed.

The active development workstream is PWA/Web Push notifications. Home Assistant is the next major
planned bridge after push notifications. See [`docs/04_Development_Roadmap.md`](docs/04_Development_Roadmap.md).

## Tech stack

- **Backend:** Python · Django · Django REST Framework · PostgreSQL
- **Frontend:** React · TypeScript · Vite · TailwindCSS
- **Architecture:** Django modular monolith, API-first, Docker Compose
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

```bash
cp .env.example .env
# edit local secrets/settings

docker compose up --build
```

For bind-mounted development/hot reload:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Default direct development endpoints:

- backend health: `http://localhost:8000/api/v1/health/`
- frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`

## Updating a running base-compose deployment

The base Compose file builds application source into the backend/frontend images. A plain
`git pull` does not replace code inside already-built images.

Typical update sequence:

```bash
git pull
docker compose build homestack-backend homestack-frontend
docker compose up -d
docker exec homestack-backend python manage.py migrate
curl -fsS http://127.0.0.1:8000/api/v1/health/
```

Then verify the trusted LAN origin:

```bash
curl -I https://homestack.moosesoftwares.com
curl -I https://homestack.moosesoftwares.com/api/v1/health/
```

A future operational-hardening milestone will replace this manual sequence with one supported
deployment command and move the live stack away from development application servers.

## Current live-serving caveat

The current container definitions still use Django `runserver` and the Vite development server.
They work behind the LAN reverse proxy, but they are not the intended final production-serving
architecture. Production WSGI/static serving and tighter Docker-network exposure are explicit
near-term roadmap work before any public exposure is considered.

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

- [`HANDOVER.md`](HANDOVER.md) — current state and what to do next;
- [`docs/00_README_and_Changelog.md`](docs/00_README_and_Changelog.md) — settled decisions and doc map;
- [`docs/01_Master_Software_Specification.md`](docs/01_Master_Software_Specification.md) — product contract;
- [`docs/04_Development_Roadmap.md`](docs/04_Development_Roadmap.md) — current/future sequencing;
- [`docs/05_Security_Architecture_Document.md`](docs/05_Security_Architecture_Document.md) — security contract;
- [`VERSION_HISTORY.md`](VERSION_HISTORY.md) — historical release chronology.

Do not turn `HANDOVER.md` back into a permanent implementation diary; Git history and
`VERSION_HISTORY.md` already provide that history.