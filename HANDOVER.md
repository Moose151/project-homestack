# HANDOVER.md — HomeStack

> **Read this first if you are a coding assistant.** This file is intentionally short and current.
> It explains what HomeStack is, the rules that must not be broken, the live deployment, current
> priorities, and where to find canonical detail. Historical implementation logs belong in
> `VERSION_HISTORY.md` and Git history — do not turn this file back into a session diary.

---

## 1. What HomeStack is

HomeStack is a secure, modular, **self-hosted household management platform for one household**.
It runs on an always-on home server through Docker Compose and is already in daily household use.

The product is centred on:

- **Hub** — what needs attention today.
- **Calendar** — the shared household timeline.
- **People** — household members and non-login people used throughout the system.
- **Opt-in nodes** — broad household domains with their own records/workflows.
- **Responsive web/PWA** — the primary everyday surface on phone and desktop.
- **Kiosk** — a shared child-friendly household surface.

HomeStack may eventually be released as a **self-hosted product other households run themselves**.
It is not being designed as SaaS.

---

## 2. Current live deployment

The live household instance runs on the home server with Docker Compose.

Current LAN URL:

```text
https://homestack.moosesoftwares.com
```

HTTPS is provided outside the HomeStack Compose stack by the existing **Nginx Proxy Manager**.
A real Let's Encrypt certificate is issued by NPM through a **Cloudflare DNS-01 challenge**.
**Pi-hole** resolves `homestack.moosesoftwares.com` to the server's LAN address
(`192.168.1.125`) so the app remains LAN-only.

No router port forwarding is required for certificate issue/renewal and HomeStack is **not
publicly exposed**.

Current HomeStack services are:

- `homestack-postgres` — PostgreSQL 16.
- `homestack-backend` — Django/DRF.
- `homestack-frontend` — React/TypeScript/Vite.

The current base stack still runs Django `runserver` and the Vite development server. This is the
main production-readiness issue now that Web Push is shipped. The next engineering phase should
replace those development servers with a production WSGI/static frontend path and tighten container
network exposure.

### Live HTTPS environment

The live `.env` must include the LAN hostname/IP plus the trusted public hostname, including:

```text
HOMESTACK_PUBLIC_HOSTNAME=homestack.moosesoftwares.com
DJANGO_ALLOWED_HOSTS=...,192.168.1.125,homestack.moosesoftwares.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://homestack.moosesoftwares.com
```

`config.settings.prod` is the recommended live setting module because it already contains the
secure-proxy/cookie behaviour expected behind NPM. Confirm the actual live value before assuming
that switch has happened.

---

## 3. Canonical documentation

The canonical documentation lives in `docs/`. If stale prose or a historical checklist conflicts
with the canonical docs, the canonical docs win.

Read these first:

- `00_README_and_Changelog.md` — decisions D1–D24 and documentation map.
- `01_Master_Software_Specification.md` — product vision, node model and scope.
- `02_Software_Architecture_Document.md` — architecture and shared boundaries.
- `03_Database_Design_Document.md` — schema conventions.
- `04_Development_Roadmap.md` — current sequencing and future gates.
- `05_Security_Architecture_Document.md` — auth, permissions, sensitivity and remote-access gate.
- `06_API_Specification.md` — API conventions/route ownership.
- `07_UIUX_Design_Guide.md` — responsive/kiosk design rules.
- `08_Coding_Standards_and_Project_Structure.md` — implementation standards.
- `09_Node_Model_Decision_Record.md` — deliberate node boundaries.
- `10_Future_Features_Parking_Lot.md` — genuinely deferred ideas.

Important newer/current specs:

- `23_Core_Hub.md`
- `24_Core_Calendar.md`
- `25_Node_Homestead.md`
- `26_Node_Home_Assistant.md`
- `27_Node_Fitness.md`
- `28_Core_Corners.md`
- `29_Core_Link_Import.md`
- `30_Core_Daily_Coordination.md`
- `31_Core_Manage_HomeStack.md`
- `32_Core_Notifications_and_Push.md` — shipped notification/PWA contract.
- `33_Node_Books.md` — shipped Books domain.
- `34_Recommended_Next_Steps.md` — practical production-readiness/reliability plan.

`VERSION_HISTORY.md` is the release chronology. Do not duplicate that history here.

---

## 4. Non-negotiable architecture rules

1. **One household per install; keep `household_id` (D1/D2).** No SaaS tenancy/signup/billing.
2. **API-first (D3).** Business logic belongs in the backend.
3. **Thin event interface, no durable bus (D4)** until measured need justifies one.
4. **No Redis/Celery by default (D5).** Scheduled work uses management commands/cron for now.
5. **Shared session auth (D6).** Avatar/PIN everyday login; password re-auth for sensitive areas.
6. **Calendar has one source of truth (D7).** Owning records own dates; use scheduling helpers.
7. **One general recurrence format (D8).** RRULE/`recurrence_rule` except bounded D23 rotations.
8. **Permission-aware search/projections (D9/D10).** Never aggregate inaccessible data first.
9. **Central backend permissions (D10).** Frontend hiding is not authorization.
10. **Shared attachment security (D11).** No per-node file-security systems.
11. **Users act; People are subjects (D12).** Do not collapse the concepts.
12. **Meridian and Solace are native domains (D13/D14).** No iframe/generic integration shell.
13. **No household-specific schema/business logic (D15).**
14. **Calendar Django app is `scheduling` (D16).**
15. **Backup means restore capability (D17).**
16. **Rotating schedules are calculated cycles + sparse exceptions (D23).**
17. **Fitness is separate from medical Health (D24).**

Keep views thin. Reads belong in `selectors`; writes/business transitions belong in `services`.
Do not import another node's models merely to make a cross-node feature convenient.

---

## 5. Current product state

Major shipped areas include:

- Core auth, People/Users, roles/permissions, audit, backups and protected attachments.
- Hub, Calendar, global search and notifications.
- Atlas notes/to-do/Grocery/Shopping/reminders/Agenda.
- Native Meridian tasks/rewards/points workflows.
- Education, Home Wiki and Pets.
- **Books** personal shelves, per-User ratings/notes and shared Book Clubs/up-next queue.
- Homestead rooms/planning/maintenance/appliances/services/cover/pools/utilities/floor plan.
- Native Solace/Money.
- Fitness & Training.
- Travel trips/bookings/costs/itinerary.
- Corners and safe link/product/book enrichment/watch infrastructure.
- Manage HomeStack guides/version history/configuration.
- Trusted LAN HTTPS.
- **PWA/Web Push notifications (v0.34.10–v0.34.13)** — preferences, per-device subscriptions,
  VAPID delivery, quiet hours, household-activity bundling, fixed 24h/morning reminders,
  countdown digest, sensitive-safe push gating and service-worker/PWA support.

The completed notification branch reported **875 backend tests green** and a clean frontend
TypeScript check. Live deployment/device validation is still required below.

---

## 6. Active/recommended next phase

**Production readiness and reliability** is now the recommended primary engineering workstream.
Use `docs/34_Recommended_Next_Steps.md` for the practical plan and
`docs/04_Development_Roadmap.md` for canonical sequencing.

Recommended order:

1. replace Django `runserver` and Vite dev serving with production serving;
2. reduce unnecessary LAN-exposed database/backend/frontend ports;
3. create one supported deploy command with migration + smoke validation;
4. add frontend unit/E2E testing and CI;
5. establish encrypted off-server backup + recovery validation;
6. add small operational/System Health visibility;
7. add passkeys/2FA before any public remote-access plan.

After the reliability baseline: Home Assistant, Hearth, Travel finishing work and later Health.

Explicitly avoid generic plugins/integrations, Kubernetes/microservices, Redis/Celery without
measured need, or public exposure before the Security Architecture gate is satisfied.

---

## 7. Notification deployment requirements

The Web Push implementation is merged, but the live server must still be configured and validated.

### Deploy code and migrations

```bash
docker compose build homestack-backend homestack-frontend
docker compose up -d
docker exec homestack-backend python manage.py migrate
```

Current notification migrations after `0001_initial` are:

```text
notifications.0002_notificationpreference_usernotificationsettings_and_more
notifications.0003_pushdevice
notifications.0004_notificationreminderlog
```

### Configure VAPID

Required deployment values:

```text
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=
```

Generate keys with:

```bash
docker exec homestack-backend python manage.py generate_vapid_keys
```

Put the values in the live `.env`, then recreate/restart the backend as required. Never commit the
private key. Push gracefully no-ops when VAPID is not configured.

### Schedule reminder/countdown delivery

Run at least hourly:

```bash
docker exec homestack-backend python manage.py notifications_run_scheduled
```

The command is idempotent and currently handles:

- fixed 24-hour reminders for standalone Calendar and Atlas-sourced Calendar entries;
- morning-of reminders at each User's configured `morning_time`;
- the daily enabled Hub countdown digest.

It is deliberately **not** a generic per-domain/configurable-lead-time reminder engine.

### Real-device validation

Before treating the live rollout as fully verified:

- register at least two household users/devices with different preferences;
- send a device test push;
- confirm normal push arrives while HomeStack is closed;
- confirm quiet hours suppress normal push;
- confirm the fixed 24h/morning scheduled behaviour and countdown do not double-send on rerun;
- confirm sensitive/re-auth-required sources cannot expose protected lock-screen content;
- tap pushes and verify the destination re-checks current permissions;
- test expired/revoked subscription behaviour;
- on iOS, test an **installed Home Screen PWA** — a normal Safari tab is insufficient.

---

## 8. General deployment workflow

The home server uses **Docker**, not Podman.

After pulling code that changes baked images:

```bash
docker compose build homestack-backend homestack-frontend
docker compose up -d
```

After any deployment that may include migrations:

```bash
docker exec homestack-backend python manage.py migrate
docker exec homestack-backend python manage.py showmigrations
```

Do not assume image rebuilds apply database migrations.

Useful checks:

```bash
docker compose ps
docker logs --tail=200 homestack-backend
docker logs --tail=200 homestack-frontend
curl -I https://homestack.moosesoftwares.com
curl -I https://homestack.moosesoftwares.com/api/v1/health/
```

Before risky migrations/data changes, take or verify a backup according to `docs/restore.md`.

---

## 9. Known deployment/security follow-ups

- Confirm the live server is actually using the intended production Django settings.
- Confirm a real authenticated **write** over the trusted HTTPS origin, not only health checks.
- Complete the Web Push VAPID/cron/real-device rollout above.
- Solve production static/admin assets as part of the production-serving work.
- HomeStack remains LAN-only; do not add router port forwarding as a shortcut.
- If remote access is pursued, follow `05_Security_Architecture_Document.md` rather than assuming
  HTTPS alone makes the app internet-ready.

---

## 10. Working and validation rhythm

1. Read the relevant canonical spec and shared architecture/security/coding rules.
2. Check current implementation before designing duplicate capability.
3. Write permission/security regression tests first where access boundaries change.
4. Backend: model/migration → selectors/services → serializers/views/URLs → tests.
5. Frontend: types/client → shared components → feature UI.
6. Run focused tests plus appropriate full-suite/type/build checks.
7. Update the canonical spec if the contract changed.
8. Add concise release chronology to `VERSION_HISTORY.md` when appropriate.
9. Keep `HANDOVER.md` current rather than appending session history.

Backend tests intentionally support SQLite as well as the PostgreSQL live environment; preserve the
established fallback strategy for Postgres-specific features where required.

---

## 11. Handover maintenance rule

Only edit this file when one of these changes:

- live deployment shape;
- a non-negotiable design rule;
- current product status;
- active/near-term priorities;
- a known operational blocker/gotcha;
- the canonical documentation map.

For ordinary feature completion, update the owning spec and `VERSION_HISTORY.md`. Git already
preserves detailed implementation chronology.