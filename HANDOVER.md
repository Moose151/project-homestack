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

The base Compose file is the **production** stack: the backend runs **gunicorn** and the frontend
serves a **built React bundle from nginx**. Django `runserver` and the Vite dev server now exist
only in `docker-compose.dev.yml`. Django's static files are collected at image build time and
served by WhiteNoise, so admin stays styled under `DEBUG=False`.

`docs/35_Production_Serving_and_Deployment.md` is canonical for how this is served, deployed,
smoke-tested and rolled back.

Production network hardening is complete: the production Compose stack publishes no HomeStack
PostgreSQL/backend/frontend host ports; Nginx Proxy Manager reaches the app over the external
`proxy` Docker network; PostgreSQL stays isolated on `project-homestack_private`.

The next production-readiness work after this branch is review/live adoption of the safe one-command
deployment script (`scripts/deploy-production.sh`), then CI, off-server backup validation and
System Health.

### Live HTTPS environment

The live `.env` must include the LAN hostname/IP plus the trusted public hostname, including:

```text
HOMESTACK_PUBLIC_HOSTNAME=homestack.moosesoftwares.com
DJANGO_ALLOWED_HOSTS=...,192.168.1.125,homestack.moosesoftwares.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://homestack.moosesoftwares.com
```

`config.settings.prod` is now **pinned by `docker-compose.yml`** in the backend service's
`environment:` block, which takes precedence over `.env`. A stale `DJANGO_SETTINGS_MODULE` in the
live environment file can no longer put production on development settings.

Production settings derive `https://$HOMESTACK_PUBLIC_HOSTNAME` into both `ALLOWED_HOSTS` and
`CSRF_TRUSTED_ORIGINS`, so those entries no longer have to be maintained by hand.

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
- `35_Production_Serving_and_Deployment.md` — how production is served, deployed and rolled back.

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
- **Production serving (v0.35.0)** — gunicorn, a built React bundle on nginx with SPA fallback,
  WhiteNoise static/admin handling, verified production settings and an explicit dev/prod Compose
  split. See `docs/35_Production_Serving_and_Deployment.md`.

Web Push is live and validated on real devices; VAPID and the hourly `notifications_run_scheduled`
job are configured on the server.

**Mobile UX v1 (v0.36.11, complete on `main`)** — owner-directed rework of the
phone experience per `docs/36_Mobile_UX_Strategy_and_Implementation_Plan.md`. Phases 1–7 done:
a Playwright mobile-viewport acceptance suite (API-mocked — see `frontend/e2e/README.md` for why
it must never hit the real backend), a shared `src/components/mobile/` primitives layer, the
redesigned AppShell (simplified mobile top bar with contextual Back; fixed Home/Add/More bottom
nav with two configurable shortcuts), Calendar as the mobile reference implementation
(phone-default Agenda view, a horizontal-day-strip Week view, simplified Month cells, a
full-height event sheet), a phone dashboard for Homestead's nine sections (preserving the
`?tab=` deep-link contract six other places rely on) plus a list-first Rooms default and a
full-sheet room-item editor, `Modal size="full"` sheets for Solace's Add Bill/Bucket/Purchase/
Payday and Edit Bill (previously zero `Modal` usage anywhere in that page), and immediate-save
notification-category switches plus a real settings-directory section (including a "People &
access" link that was previously unreachable from Settings at all). Two rounds of external review
before merge, both fully corrected on this branch (docs/36 Phase 3 and Phase 4 "Correction pass"
sections have the full lists). Round 1 (pre-Phase-4, foundation issues): Back was unsafe on a cold
deep link/PWA launch (now falls back to the stack's base route rather than a bare `navigate(-1)`);
several shell/dialog controls were under the 44px touch-target baseline; the More sheet had a
second, thinner dialog-accessibility implementation instead of reusing `Modal`'s (extracted into a
shared `useDialogA11y` hook); the bottom-bar shortcut list couldn't persist genuinely zero
shortcuts and didn't backfill a slot when a pinned node got disabled. Round 2 (post-Phase-4,
Calendar-specific): Agenda's Previous/Next/Today were inert (Agenda ignores `anchor` entirely,
now hidden rather than faked); the floating Add button and desktop `+ Event` silently created
against `new Date()` instead of the selected day in Week view; the Event title field's `autoFocus`
was being overridden by the dialog hook's own autofocus fallback (now uses `data-autofocus`); "My
events only" compared assignee arrays by reference and so hid the user's own events (now an
ID-membership check); `MobileScreenHeader`'s `onBack` is now a compile-time requirement whenever
`showBack` is true, closing off the same unsafe-Back failure mode at the type level so a future
screen can't reintroduce it by omission. Also found and fixed along the way: `AppShell`'s `<main>`
was never actually width-constrained to the viewport (a flex-item `min-width: auto` issue, latent
until Calendar's week-day-strip was wide enough to expose it).

Phase 8 (Atlas, Meridian, Education, Pets, Fitness, Corners — all six daily-use nodes) is complete
for the software-side mobile pass. Atlas's "Lists" tab and Pets' per-pet card both used to stack every item's full,
expanded contents on one page; both now show a phone summary row that opens a focused detail
sheet (Atlas reuses the existing `ListCard`; Pets extracts a shared `PetDetailContent` used by
both the new sheet and the desktop card's inline expand, so there's one implementation, not
two). Meridian's eight-tab bar becomes Tasks/Rewards/My progress/Manage on phone, exactly the
model the doc names, with `?tab=` still the single source of truth so nothing else that deep
links into Meridian had to change. Education gained a "Today"/"Due soon" landing tab (now the
default, replacing "My Profile") and assignment notes/files moved from an inline accordion into
a real detail sheet. Fitness's live-workout screen was already close to the doc's target and was
left alone; the page chrome (header, 5-tab bar) now hides while a session is actually active,
which is the "reduce unrelated navigation/noise" ask. Corners was already close to the doc's
model; its small stat-link cards became proper `MobileListRow` destinations. Found and fixed
along the way: `CornerPage`'s `corner?.collections.filter(...)` only short-circuited when
`corner` itself was nullish, not when it resolved truthy-but-malformed — with no root error
boundary, that crashed the entire app, not just Corners; latent in the existing code, not
introduced this phase.
The v0.36.7 correction pass added cold Atlas `?item=` phone deep-link opening/highlighting,
sanitized unauthorized Meridian `?tab=settings`, moved Education assignment creation to a full
sheet, linked Education search results to exact assignments/classes and moved pet treatment/
appointment edit flows into a focused state inside the pet sheet. Pets now receives exact pet/
treatment/appointment deep links.

Phase 9 (Books, Home Wiki, Travel — the lower-frequency content/planning nodes) is complete for
the software-side mobile pass.
All three already had good bones (Books' shelf/card model, Home Wiki's search-first layout,
Travel's `?trip=`-based per-trip project view all pre-dated this phase and were left alone); the
common gap across all three was "long inline forms" — Add/Edit book, wiki page create/edit,
trip/booking/itinerary forms all used to expand inline and push the rest of the page down, now
`Modal size="full"` everywhere, the same sheet pattern used since Calendar's Phase 4. Home Wiki
also gained a proper "tap to read full-screen, Edit as an action inside" detail sheet in place of
an inline-body-expand-then-inline-edit-form sequence. Found and fixed along the way: Books' book
grids had no explicit base `grid-cols-1`, the CSS Grid analogue of the AppShell `<main>` flex bug
from Phase 4 — a grid item's default `min-width: auto` let a wide card dictate the implicit
column's width instead of the container's, pushing the grid past the viewport at 320px.
The v0.36.7 correction pass added a focused book detail sheet, URL-addressable Wiki pages
(`?page=`), sticky Travel form footers and itinerary-form Playwright coverage.

Phase 5-7 correction completion in v0.36.7: Money now has a true phone home/current-position
screen with destination rows instead of the five-primary-tab selector; Notifications now uses
category drill-down for In-app/Push/Mine-only rather than rendering every category expanded;
Manage HomeStack opens as a phone settings directory with focused sections; Homestead overview
uses shared data instead of duplicate hidden mobile/desktop effect paths; Meridian setting
switches use 44px hit areas.

Final pre-hardware corrections in v0.36.8: `main` is merged into the feature branch (including
the live Solace health fix/test); nested dialogs are stack-aware; Homestead Floor Plan is a real
full-screen phone viewer; Notifications identifies and prioritizes **This phone** with touch-sized
device actions; and Hub has a phone daily feed plus prominent Search. The complete mocked browser
suite is green across its four viewport projects. The completed feature work is now on `main`.

Everyday-action follow-up in v0.36.9: Fitness defaults training to the person linked to the current
login, supports searchable/type-filtered mid-workout exercise selection, and exposes recent
exercise history from each live exercise card. Corners uses one household-member dropdown instead
of a row of name buttons. Money's phone Coming up list can mark an occurrence paid in place.

**Phase 10 live acceptance is complete.** The redesigned mobile experience has been deployed to
the live HTTPS HomeStack installation and tested successfully on real devices, including the
real-world PWA/push/safe-area/browser behaviours that could not be proven by the mocked Playwright
suite alone. Mobile UX v1 is now closed out; preserve the completed automated coverage for
regression protection, but do not treat Mobile UX as active feature work.

---

## 6. Active/recommended next phase

**Production readiness and reliability** is the active engineering workstream now that Mobile UX
v1 is complete.
Use `docs/34_Recommended_Next_Steps.md` for the practical plan and
`docs/04_Development_Roadmap.md` for canonical sequencing.

Recommended order:

1. ~~replace Django `runserver` and Vite dev serving with production serving~~ — **done, v0.35.0**;
2. ~~reduce unnecessary LAN-exposed database/backend/frontend ports~~ — **done, v0.37.x**;
3. create one supported deploy command with migration + smoke validation — **prepared for review
   in `scripts/deploy-production.sh`**;
4. add frontend unit/E2E testing and CI;
5. establish encrypted off-server backup + recovery validation;
6. add small operational/System Health visibility;
7. add passkeys/2FA before any public remote-access plan.

After the reliability baseline: Home Assistant, Hearth, Travel finishing work and later Health.

**Docker/network hardening status (v0.37.x):** complete. The actual inspected Nginx Proxy Manager
deployment is container/service `nginx-proxy-manager`, Compose project `nginx-proxy-manager`,
external network `proxy`, with ports `80`, `81` and `443`. HomeStack production Compose publishes
no PostgreSQL/backend/frontend host ports. NPM routes the main app to
`homestack-frontend:5173`, and `/api/` plus `/admin/` to `homestack-backend:8000` over Docker DNS.
Frontend is attached only to `proxy`; backend is attached to `proxy` plus
`project-homestack_private`; PostgreSQL is attached only to `project-homestack_private`.
Development Compose remains isolated on `homestack_dev`.

**Deployment automation status (v0.37.5):** `scripts/deploy-production.sh` is prepared for review.
It performs preflight, backup freshness/completeness gating, fast-forward-only Git update,
build-before-promotion, explicit `--migrate` handling, backend/frontend recreation one at a time,
NPM `nginx -t`/reload after each app-container promotion, HTTPS/API checks and final topology
validation. Do not use it for a live deployment until the branch has been reviewed and merged.

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
notifications.0005_pushdevice_browser_pushdevice_label_is_custom_and_more
```

`0005` carries a data step that renames already-registered devices from the old client-side
names ("This device", "Android device") to server-generated ones ("Firefox on Linux"). Devices
registered before it do not need re-registering — but the rename only happens on `migrate`.

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

The home server uses **Docker**, not Podman. Plain `docker compose` is the **production** stack;
development needs the explicit override (see §2 and `docs/35_Production_Serving_and_Deployment.md`).

After pulling code that changes baked images — validate the new image **before** promoting it:

```bash
docker compose build homestack-backend homestack-frontend

# One-off containers from the newly built image; the running containers are untouched, so a
# non-zero exit means abandon the deploy with nothing to roll back.
docker compose run --rm --no-deps homestack-backend python manage.py check     # prod config checks
docker compose run --rm --no-deps homestack-backend python manage.py migrate

docker compose up -d
docker exec homestack-backend python manage.py showmigrations | tail -20
```

Both images now bake application source *and build artefacts* — the frontend bundle and Django's
collected static files. A `git pull` alone changes neither; always rebuild.

Do not assume image rebuilds apply database migrations, and do not skip the `check` step on a
release with no migrations — it is what rejects a bad `.env` while rollback is still free. Full
procedure, including the destructive-migration exception, is in
`docs/35_Production_Serving_and_Deployment.md` §11.

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

- Reduce LAN-exposed database/backend/frontend ports — deliberately unchanged by v0.35.0 so that
  the production-serving change could be rolled back without touching Nginx Proxy Manager.
- Django admin is reachable only on the backend port: NPM routes just `/api/` to the backend, so
  `/admin/` falls through to the SPA. Its assets are correct; reaching it over HTTPS needs two
  optional NPM locations (`docs/35_Production_Serving_and_Deployment.md` §10). Note that secure
  cookies mean admin login over plain HTTP will not work, and turning them off is not an
  acceptable workaround.
- No Content-Security-Policy on the frontend yet; it needs authoring against the real bundle.
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
