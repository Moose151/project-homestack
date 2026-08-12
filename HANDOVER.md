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

The canonical documentation lives in `docs/`. If a stale comment, historical changelog entry or
old `.docx` conflicts with the canonical docs, the canonical docs win.

Read these first:

- `00_README_and_Changelog.md` — architectural/product decisions (D1–D24) and documentation map.
- `01_Master_Software_Specification.md` — product vision, current node model and scope.
- `02_Software_Architecture_Document.md` — modular-monolith architecture and shared boundaries.
- `03_Database_Design_Document.md` — schema conventions.
- `04_Development_Roadmap.md` — current sequencing and future gates.
- `05_Security_Architecture_Document.md` — authentication, permissions, sensitive data and
  remote-access gate.
- `06_API_Specification.md` — API conventions/route ownership.
- `07_UIUX_Design_Guide.md` — responsive/kiosk design rules.
- `08_Coding_Standards_and_Project_Structure.md` — mandatory code structure and conventions.
- `09_Node_Model_Decision_Record.md` — why HomeStack uses a deliberately small node set.
- `10_Future_Features_Parking_Lot.md` — deferred ideas; not authority to create new nodes.

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
- `32_Core_Notifications_and_Push.md` — shipped Web Push/PWA notification contract.
- `33_Node_Books.md` — shipped personal reading / Book Clubs domain.
- `34_Recommended_Next_Steps.md` — practical execution plan for the current production-readiness
  and reliability phase.

`VERSION_HISTORY.md` is the historical release record. Do not duplicate that history here.

---

## 4. Non-negotiable architecture rules

These are settled product/architecture decisions. If a new requirement appears to conflict with
one of them, surface the conflict rather than silently bypassing it.

1. **One household per install; keep `household_id` (D1/D2).** Do not build SaaS or multi-tenant
   signup/billing behaviour.
2. **API-first (D3).** Business logic lives in the backend; clients use `/api/v1/`.
3. **Thin event interface, no durable event bus (D4).** Node decoupling uses the existing Django
   signal/event boundary. Do not introduce an events table/broker without a demonstrated need.
4. **No Redis/Celery by default (D5).** Scheduled work uses management commands/cron until real
   workload requirements justify a worker/broker.
5. **Shared session authentication (D6).** Everyday avatar/PIN login; password re-authentication
   for sensitive areas. PINs/passwords use Argon2id.
6. **Calendar has one source of truth (D7).** Node records own their dates. Nodes use the shared
   scheduling helper; they do not create parallel Calendar records manually.
7. **One recurrence format (D8).** Use RRULE through `recurrence_rule`; do not add another generic
   repeat field.
8. **Search through selectors with permission/visibility filtering (D9/D10).** Never create a
   search path that bypasses record visibility.
9. **Central permissions (D10).** No ad-hoc permission logic in views. Permission tests come first.
10. **Attachments use shared visibility/sensitivity controls (D11).** Do not invent per-node file
    security systems.
11. **People and Users are distinct (D12).** Users authenticate/own/audit; People are household
    subjects/assignees and may not have logins.
12. **Meridian and Solace are native HomeStack domains (D13/D14).** Do not recreate iframe or
    generic integration shells around the legacy apps.
13. **No household-specific schema/logic (D15).** Real household data is fine; hard-coded family
    assumptions are not.
14. **The Calendar Django app is `scheduling` (D16).** Do not rename it to `calendar`.
15. **Backup work includes restore (D17).** A backup feature is incomplete if restore is untested.
16. **Rotating Calendar layers are calculated cycles plus sparse exceptions (D23).** Do not
    materialise years of daily events.
17. **Fitness is separate from medical Health (D24).** Social training/workouts/records belong to
    Fitness; medical/injury/diagnosis data belongs to the stronger Health privacy boundary.

### Per-app layering

Keep views thin. Reads belong in `selectors`; writes/business rules belong in `services`.
Permission/visibility behaviour remains central and test-first.

Typical app shape:

```text
models.py
serializers.py
selectors.py
services.py
views.py
urls.py
events.py
tasks.py
tests/
```

Do not import another node's models simply to make a cross-node feature convenient. Use the
existing shared service/event contracts.

---

## 5. Current product state

HomeStack is no longer a walking skeleton or an undeployed pilot. It is running on the household
server and is being used with real data.

Major shipped areas include:

- Core auth, People/Users, roles/permissions, audit and backups.
- Hub, Calendar, global search, notifications and attachments.
- Atlas with notes, to-do, Grocery, Shopping, reminders and Agenda-style coordination.
- Native Meridian household tasks/rewards/points workflows.
- Education for courses, assessments, timetable/events and study workflows.
- Home Wiki and Pets.
- **Books** with personal reading shelves, per-User rating/notes and shared Book Clubs/up-next queue.
- Homestead including rooms/planning, maintenance, appliances, services, improvements, costs &
  cover, pools/spas, utility usage and the interactive floor plan.
- Native Solace/Money with bills, pay cycles, budget/allocation and household finance workflows.
- Fitness & Training as a separate non-medical node.
- Travel with trips, bookings/costs, trip type and itinerary items.
- Corners, suggestions/reactions and shared link-import/product/book enrichment/watch infrastructure.
- Manage HomeStack guides/version history and household configuration surfaces.
- Trusted LAN HTTPS at `homestack.moosesoftwares.com`.
- **PWA/Web Push notifications (v0.34.10–v0.34.13)** — per-user preferences, per-device
  subscriptions, VAPID delivery, quiet hours, bundled household activity, scheduled reminders,
  countdown digest, sparse sensitive-safe payloads and PWA/service-worker support.

The completed notification branch reported **875 backend tests green** and a clean frontend
TypeScript check. Treat those as the implementation validation result; still perform the real live
server/device deployment checks below.

Use `VERSION_HISTORY.md` for exact release-by-release details rather than repeating them here.

---

## 6. Active work and near-term priorities

### Active/recommended next phase

**Production readiness and reliability** is now the recommended primary engineering workstream.
Use `docs/34_Recommended_Next_Steps.md` as the practical plan and
`docs/04_Development_Roadmap.md` for canonical sequencing.

Recommended order:

1. **Production-serving hardening** — replace Django `runserver` and Vite dev serving with a
   production WSGI server and production-built frontend/static serving.
2. **Reduce exposed service ports** — prefer an internal/shared Docker network behind NPM and stop
   unnecessarily publishing PostgreSQL/backend/frontend to the LAN.
3. **Automated deploy command** — backup/preflight, build, migrations, restart and smoke checks in
   one supported workflow.
4. **CI and frontend/E2E tests** — backend suite, migration drift, frontend type/build/unit tests
   and a small Playwright critical-flow suite.
5. **Off-server encrypted backup + recovery validation** — HomeStack now contains important
   household data and needs a credible server/storage-loss recovery path.
6. **Operational/System Health surface** where it provides useful visibility without rebuilding
   Uptime Kuma/Dozzle.
7. **2FA/passkeys for adult/admin accounts** before any public remote-access plan.

### Feature priorities after reliability work

- Resume the **Home Assistant bridge (M5.5)** now that HTTPS and Web Push prerequisites exist,
  after the production/recovery baseline is in better shape.
- **Hearth/meal planning** can use Atlas Grocery rather than inventing another grocery store.
- Finish Travel packing/protected-document slices when useful.
- Health remains deliberately later because it raises the sensitivity/security bar.

### Explicitly not a priority

- New generic integration/plugin framework.
- Kubernetes/microservices.
- Redis/Celery without measured need.
- More top-level nodes merely because a feature could be separated.
- Public exposure before the Security Architecture remote-access gate is satisfied.

---

## 7. Notification deployment requirements

The Web Push implementation is merged, but the live server must still be configured correctly.

### Required deployment steps

The notification work adds backend dependencies and migrations. After pulling it to the live server:

```bash
docker compose build homestack-backend homestack-frontend
docker compose up -d
docker exec homestack-backend python manage.py migrate
```

Relevant notification migrations include:

```text
notifications.0002_preferences_and_push_subscriptions
notifications.0003_notification_bundle_key
notifications.0004_notification_preference_lead_time_minutes
```

### VAPID configuration

Web Push requires these deployment secrets/settings:

```text
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_SUBJECT=
```

Generate a key pair with:

```bash
docker exec homestack-backend python manage.py generate_vapid_keys
```

Put the generated values in the live `.env`, then recreate/restart the backend so clients receive
the configured public key. Never commit the private key. Push gracefully disables when VAPID is
not configured, but device registration/delivery will not function.

A test push can be sent through the implemented device test endpoint once a device is registered.

### Scheduled notification command

Run the dispatcher at least hourly:

```bash
python manage.py notifications_run_scheduled
```

In Docker/host scheduling, invoke the equivalent command inside `homestack-backend`. It handles
household-timezone-aware scheduled reminders/countdown delivery with duplicate claiming.

### Real-device validation

Before treating the live rollout as fully verified:

- register at least two household users/devices with different preferences;
- confirm push arrives while HomeStack is closed;
- confirm quiet hours and lead times behave correctly;
- confirm sensitive/re-auth-required sources do not expose lock-screen detail;
- tap pushes and verify the destination re-checks current permissions;
- test expired/revoked subscription behaviour;
- on iOS, test from an **installed Home Screen PWA** — a normal Safari tab is not sufficient for
  iOS Web Push.

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

Do not assume image rebuilds apply database schema changes. Forgetting `migrate` has caused real
live failures before.

Useful checks:

```bash
docker compose ps
docker logs --tail=200 homestack-backend
docker logs --tail=200 homestack-frontend
curl -I https://homestack.moosesoftwares.com
curl -I https://homestack.moosesoftwares.com/api/v1/health/
```

Before risky migrations or data-changing maintenance, take/verify a backup according to
`docs/restore.md` and the backup service documentation.

---

## 9. Known deployment/security follow-ups

- Confirm the live server is actually using `DJANGO_SETTINGS_MODULE=config.settings.prod` rather
  than merely documenting the intended switch.
- Confirm a real authenticated **write** over `https://homestack.moosesoftwares.com`, not only the
  health endpoint, after security/environment changes.
- Complete the Web Push VAPID/cron/real-device rollout described above.
- Django admin static assets need a production-static solution if the admin UI is expected to
  remain styled with `DEBUG=0`; this is naturally addressed by production serving work.
- HomeStack is LAN-only. Do not add router port forwarding as a shortcut.
- If remote access is pursued later, follow `docs/05_Security_Architecture_Document.md` rather
  than assuming HTTPS alone makes the application ready for the internet.

---

## 10. Working and validation rhythm

For normal application work:

1. Read the relevant canonical spec and the shared architecture/security/coding rules.
2. Check current implementation before designing a duplicate capability.
3. Write permission/security regression tests first for access-sensitive work.
4. Backend: model/migration → selectors/services → serializers/views/URLs → tests.
5. Frontend: types/client → shared components → feature UI.
6. Validate the focused tests plus the appropriate full-suite/type/build checks.
7. Update the canonical spec if behaviour/product direction changed.
8. Add a concise release entry to `VERSION_HISTORY.md` when appropriate.
9. Commit coherent work on a branch; do not use `HANDOVER.md` as a chronological progress log.

Backend tests intentionally support SQLite as well as the Postgres live environment. Guard
Postgres-only query features with an appropriate fallback where the existing test architecture
requires it.

---

## 11. How to leave work for the next assistant

Keep this file current, not historical.

Only edit `HANDOVER.md` when one of these changes:

- the live deployment shape;
- a non-negotiable design rule;
- current product status;
- active/near-term priorities;
- a known operational blocker/gotcha;
- the canonical documentation map.

For ordinary feature completion, use the relevant canonical spec and `VERSION_HISTORY.md`.
Git already preserves the detailed implementation chronology.