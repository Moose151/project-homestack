# Recommended Next Steps — Production Readiness & Reliability

> **Status:** Recommended execution plan following the current Web Push/PWA work.
>
> This document is intentionally practical. It does not replace the canonical Roadmap,
> Architecture or Security documents. It translates their current direction into a clear answer
> to: **what should HomeStack do next, in what order, and what needs to be true before moving on?**
>
> Current architectural decisions remain authoritative in `00_README_and_Changelog.md`; current
> sequencing remains authoritative in `04_Development_Roadmap.md`; security gates remain
> authoritative in `05_Security_Architecture_Document.md`.

## 1. Recommendation

HomeStack has reached the point where the highest-value next phase is **not another large node**.
The application already has broad household functionality and is in real daily use. The next
engineering phase should make that application **dependable as household infrastructure**.

The recommended sequence is:

1. **Finish the current PWA/Web Push milestone.**
2. **Move immediately into production-serving and deployment hardening.**
3. **Tighten container/network exposure.**
4. **Automate deployment and smoke validation.**
5. **Add frontend/E2E testing and CI.**
6. **Strengthen backup/recovery and operational health.**
7. **Add stronger adult authentication before any public remote-access plan.**
8. Only then return to larger feature expansion such as Home Assistant, Hearth and later Health.

This is the recommended next step because HomeStack is now a live household system containing
important operational, financial and personal data. Reliability, recovery and repeatable updates
now create more value than adding another major feature area.

---

## 2. First: finish Web Push/PWA notifications

Web Push is already the active development workstream and trusted LAN HTTPS removed its previous
blocker. Complete it rather than interrupting it for the hardening work below.

Canonical implementation contract: `32_Core_Notifications_and_Push.md`.

### What needs to happen

- Per-user notification preferences.
- Per-device Web Push subscriptions.
- VAPID/Web Push delivery from the backend.
- Quiet hours and useful lead-time behaviour.
- Sparse lock-screen payloads for private/sensitive content.
- Deep links to the owning HomeStack record.
- Permission and re-authentication checks again when the notification is opened.
- Safe removal/deactivation of expired subscriptions.
- Real-device testing for at least two different household users/devices.

### Done when

Two household users can independently configure notifications, receive real push messages while
HomeStack is closed, open the correct permitted destination, and no sensitive information is
exposed through push or an unauthorised session.

Once this milestone is complete, **production readiness becomes the recommended primary engineering
workstream.**

---

## 3. Recommended next engineering phase — production serving

The live HomeStack deployment still uses development application servers. That is acceptable for
the current LAN-only stage, but it should no longer be the long-term serving model for a system the
household depends on.

Current shape:

```text
Nginx Proxy Manager
        |
        +--> Vite development server
        |
        +--> Django runserver
```

Recommended production shape:

```text
LAN client
    |
    v
Nginx Proxy Manager :443
    |
    +--> production-built React static application
    |
    +--> production WSGI Django application
              |
              v
          PostgreSQL
```

### 3.1 Backend production server

Replace Django `runserver` in the live production profile with a supported production WSGI server,
with Gunicorn being the simplest recommended choice for the current Django architecture.

What needs to happen:

- add the production WSGI dependency;
- define a production container command;
- choose sensible worker/timeout settings for the small household workload;
- preserve Django health checks and clear logging;
- validate proxy headers and secure-cookie behaviour behind Nginx Proxy Manager;
- keep the development Compose override using `runserver`/reload where useful.

Do not introduce a new application architecture simply to replace `runserver`.

### 3.2 Production frontend build

Stop using the Vite development server as the live frontend server.

What needs to happen:

- run `npm ci` and `npm run build` in a build stage;
- produce the Vite `dist` output;
- serve that static output from a small production web server or an appropriate existing proxy
  path;
- ensure SPA routes fall back correctly to `index.html`;
- preserve `/api/` proxy behaviour to Django;
- verify PWA/service-worker and push behaviour from the final production build, not only `vite dev`.

### 3.3 Production Django settings

Confirm and deliberately select the live Django production settings rather than assuming the
switch happened because the documentation recommends it.

At minimum verify:

- `DJANGO_SETTINGS_MODULE` is the intended production module;
- `DEBUG=0`/equivalent production behaviour;
- `DJANGO_ALLOWED_HOSTS` includes the trusted HomeStack hostname;
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://homestack.moosesoftwares.com`;
- secure session/CSRF cookie behaviour works through NPM;
- `SECURE_PROXY_SSL_HEADER`/proxy handling matches the NPM deployment;
- static/admin asset behaviour is explicitly solved;
- secrets remain outside the repository.

### Production-serving completion gate

Do not call this phase complete until:

- HomeStack is served without Django `runserver`;
- HomeStack is served without the Vite development server;
- login, logout, PIN login and password re-auth work through the trusted HTTPS origin;
- at least one authenticated write succeeds through the HTTPS origin;
- PWA/push still works from the production frontend build;
- backend and frontend health/smoke checks pass after container recreation.

---

## 4. Tighten Docker networking and exposed ports

The long-term live topology should expose only the services that actually need LAN ingress.
PostgreSQL should not be directly reachable from ordinary LAN clients, and Django/frontend should
prefer communication through the reverse-proxy/container network rather than broadly published host
ports.

Recommended target:

```text
LAN
 |
 v
Nginx Proxy Manager :443
 |
 +---- shared/private Docker network ----+
 |                                       |
 v                                       v
HomeStack web                         Django API
                                         |
                                         v
                                     PostgreSQL

No ordinary LAN-facing PostgreSQL port.
No ordinary LAN-facing Django development port.
No ordinary LAN-facing Vite development port.
```

### What needs to happen

- establish an explicit shared Docker network between NPM and the HomeStack ingress services;
- make PostgreSQL internal-only in the production profile;
- remove unnecessary production host publication of `5432`, `8000` and `5173` once NPM can reach
  the appropriate containers directly;
- keep development-only port publication in `docker-compose.dev.yml` or an equivalent override;
- confirm NPM admin port `81` remains LAN/admin-only;
- confirm no router port forwarding is introduced as part of this work.

### Done when

A normal household client can reach HomeStack only through the trusted HTTPS origin, while database
and internal application ports are no longer generally exposed to the LAN in the production
profile.

---

## 5. Create one supported deployment command

The current manual update sequence is easy to perform incorrectly. HomeStack has already reached a
stage where forgetting an image rebuild or migration can break the live household system.

Create one supported command, for example:

```bash
./scripts/deploy.sh
```

### The deployment workflow should perform

1. preflight checks;
2. verify/offer a current backup before risky changes;
3. fetch/use the intended code revision;
4. build production backend/frontend images;
5. run database migrations safely;
6. recreate/restart services;
7. verify container health;
8. verify backend health endpoint;
9. verify the trusted HTTPS frontend origin;
10. verify the HTTPS API health endpoint;
11. show the deployed HomeStack version/commit;
12. give clear failure/rollback guidance if a stage fails.

Useful smoke checks include:

```bash
curl -fsS https://homestack.moosesoftwares.com/api/v1/health/
curl -I https://homestack.moosesoftwares.com
```

The script must fail loudly rather than reporting success after a failed migration or failed health
check.

### Done when

A routine HomeStack update no longer requires remembering a multi-command sequence from the
Handover. One documented command performs the supported production deployment and verifies that the
result is healthy.

---

## 6. Add frontend testing and CI

The backend has strong automated coverage. The next QA gap is the frontend and full browser flow.
The objective is not thousands of UI tests; it is protection for the workflows that could make the
household system unusable if they regress.

### Recommended test stack

- **Vitest** for frontend unit/component tests.
- **React Testing Library** for user-visible component behaviour.
- **Playwright** for a small number of complete browser flows.
- **GitHub Actions** for automated verification on pull requests.

### Initial Playwright/core-flow coverage

Prioritise roughly these flows:

- password login/logout;
- avatar/PIN login;
- sensitive re-authentication;
- Hub renders and navigation works;
- Calendar opens and source deep links work;
- create/edit/complete an Atlas item;
- permission isolation between two users;
- Solace sensitive lock/re-auth behaviour;
- mobile navigation at a phone viewport;
- PWA/push subscription flow where practical in automation;
- one representative write from another important domain.

### Recommended CI checks

```text
backend tests
makemigrations --check
frontend typecheck
frontend unit tests
frontend production build
selected Playwright smoke tests
```

### Done when

A pull request cannot silently break the backend test suite, migration state, production frontend
build or a small set of critical household browser workflows without CI reporting it.

---

## 7. Strengthen backups and recovery

HomeStack is becoming a source of truth for important household information. A backup stored only
on the same server/storage device is not sufficient long-term protection.

### What needs to happen

- retain the existing database + protected-media backup contract;
- add at least one **encrypted copy off the primary HomeStack server/storage device**;
- ideally keep another copy in a different physical failure domain;
- keep backup credentials/encryption keys outside ordinary user-facing configuration and outside
  the repository;
- record last successful local and off-server backup status;
- retain checksums/integrity validation;
- periodically perform an actual restore test;
- keep `docs/restore.md` aligned with the real supported process.

A practical home deployment could use a NAS/second machine or separate physical storage for the
first off-server copy, with a second encrypted remote/offsite copy added when appropriate.

### Done when

Loss of the HomeStack server or its primary storage does not imply loss of the household database
and attachments, and a recent backup has been successfully restored in a real test.

---

## 8. Add an operational System Health surface

Once deployment and backup jobs are dependable, HomeStack should be able to tell an administrator
whether its own essential operational functions are healthy without requiring routine log reading.

Recommended Admin → **System Health** information:

- installed HomeStack version/commit;
- backend health;
- database health;
- available storage/disk warning state;
- last successful local backup;
- last successful off-server backup;
- last restore-test date where tracked;
- scheduled-command last-run/failure state;
- push dispatcher/job status;
- Home Assistant bridge health once implemented;
- links to existing operational tools such as Uptime Kuma/Dozzle rather than recreating them.

Keep this intentionally small. HomeStack should expose the health of HomeStack, not become a full
server-monitoring replacement.

---

## 9. Stronger adult authentication before public remote access

LAN HTTPS is now trusted, but HTTPS alone does not make HomeStack ready for public internet access.

Before any Cloudflare Tunnel or other public remote-access path is enabled, complete the security
gate in `05_Security_Architecture_Document.md`.

The recommended adult/admin authentication improvement is **WebAuthn/passkeys or another strong
second factor** while retaining simple PIN login for ordinary LAN/kiosk use where appropriate.

### What needs to happen before public exposure

- production serving completed;
- unnecessary service ports removed;
- strong adult/admin passwords;
- rate limiting/brute-force protection;
- 2FA/passkey capability for privileged remote access;
- sensitive-node re-authentication verified;
- secure cookie/proxy configuration verified;
- encrypted off-server backups operating;
- explicit public-exposure threat-model/security review;
- decision whether VPN-only access remains preferable.

Do **not** add router port forwarding as a shortcut around this gate.

---

## 10. Feature work after the reliability phase

Once production serving, deployment, recovery and QA are materially stronger, return to household
feature expansion according to actual use.

### 10.1 Home Assistant

Home Assistant remains the recommended next major integration after push/reliability work.
Keep D22 and `26_Node_Home_Assistant.md` intact:

- Home Assistant owns devices, state, history and automations;
- HomeStack owns People, permissions, household records and presentation mappings;
- backend-only HA token;
- explicit entity/control allowlists;
- read-only status first;
- safe low-risk controls second;
- no generic integrations framework.

### 10.2 Hearth / meal planning

Hearth is one of the strongest remaining everyday domains:

- recipes;
- meal plans;
- dinner/weekly meal view;
- recipe import;
- ingredient scaling;
- send missing ingredients into the existing **Atlas Grocery** list.

Do not create another grocery/shopping data store.

### 10.3 Documents browser

The shared attachment system already provides the important security/storage foundation. A future
first-class Documents surface can improve discoverability across manuals, receipts, insurance,
school files, pet records, warranties and contracts while preserving the owning domain record as
the source of truth.

The browser should aggregate permission-filtered attachments; it should not move or duplicate
ownership simply to make files searchable in one place. OCR can remain later.

### 10.4 Travel finishing work

Finish useful existing Travel slices rather than create a new domain:

- packing lists;
- protected travel documents;
- later optional photo/journal/map/flight enrichments where they provide real value.

The itinerary itself is already shipped.

### 10.5 Health remains later

Do not rush medical Health. It raises the highest privacy/sensitivity bar in the product.
Production serving, reliable backups, stronger adult authentication and the public-access security
posture should mature first.

Fitness remains separate from medical Health under D24.

---

## 11. Infrastructure that should remain deferred

Do not add these simply because HomeStack is becoming more mature:

- Redis/Celery without a demonstrated queue/retry/concurrency need;
- microservices;
- Kubernetes;
- generic plugin/integration marketplace;
- generic automation/workflow engine;
- durable event broker without evidence the D4 event interface is insufficient;
- AI features without a clear household workflow they improve.

The current Django modular monolith remains appropriate for the workload. Improve its production
operation before replacing it.

Web Push or Home Assistant may eventually create enough background/retry workload to justify a
worker/broker. Measure the need first.

---

## 12. Recommended delivery order

The practical order from the current state is:

```text
CURRENT
  Finish Web Push / PWA notifications
        |
        v
NEXT RECOMMENDED PHASE
  Production Django + production frontend
        |
        v
  Private/tighter Docker networking
        |
        v
  One-command deployment + smoke checks
        |
        v
  Frontend tests + Playwright + CI
        |
        v
  Encrypted off-server backups + restore testing
        |
        v
  System Health / operational visibility
        |
        v
  Passkeys/2FA + remote-access security gate
        |
        v
FEATURE EXPANSION
  Home Assistant / Hearth / Documents / Travel finishing
        |
        v
LATER SENSITIVE WORK
  Health
```

Some tasks can overlap, but this is the preferred priority order. In particular, major new feature
work should not repeatedly displace production serving, deployment reliability and recovery once
Web Push is complete.

---

## 13. Exit criteria for the reliability phase

HomeStack can reasonably be described as dependable household infrastructure when all of the
following are true:

- production Django server in use;
- production-built frontend in use;
- trusted LAN HTTPS verified for real authenticated reads/writes;
- no unnecessary database/backend/frontend development ports exposed in the production profile;
- one supported deployment command builds, migrates, restarts and smoke-tests;
- backend tests and migration checks run automatically;
- frontend production build and critical UI flows run automatically;
- at least one encrypted backup exists off the primary server/storage;
- restore has been successfully tested;
- administrators can see basic HomeStack operational health;
- adult/admin authentication has a clear stronger-auth path before public access;
- the public remote-access gate remains closed until the Security Architecture requirements are
  deliberately satisfied.

At that point, new features can be added on top of a substantially safer operational foundation
rather than increasing the amount of household data depending on a development-style deployment.
