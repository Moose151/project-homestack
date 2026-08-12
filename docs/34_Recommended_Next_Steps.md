# Recommended Next Steps — Production Readiness & Reliability

> **Status:** Recommended execution plan after completion of the PWA/Web Push implementation
> (v0.34.10–v0.34.13).
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
The application already has broad household functionality, trusted LAN HTTPS, a PWA/Web Push layer
and real daily household use. The next engineering phase should make that application **dependable
as household infrastructure**.

The recommended sequence is now:

1. **Deploy and validate the completed Web Push work on the live server.**
2. **Production-serving and deployment hardening — primary engineering phase.**
3. **Tighten container/network exposure.**
4. **Automate deployment and smoke validation.**
5. **Add frontend/E2E testing and CI.**
6. **Strengthen backup/recovery and operational health.**
7. **Add stronger adult authentication before any public remote-access plan.**
8. Then return to larger feature expansion such as Home Assistant, Hearth and later Health.

This is the recommended next step because HomeStack now contains important operational, financial
and personal household data. Reliability, recovery and repeatable updates create more value than
immediately adding another major feature area.

---

## 2. Completed prerequisite — Web Push/PWA notifications

The Web Push implementation is complete. Canonical implementation contract:
`32_Core_Notifications_and_Push.md`.

Shipped behaviour includes:

- per-user category/channel preferences and quiet hours;
- per-device Web Push subscriptions;
- VAPID delivery;
- service-worker/PWA support;
- lead-time settings;
- sparse sensitive-safe lock-screen payloads;
- permission/re-authentication checks after opening a deep link;
- expired/revoked subscription handling;
- household-activity bundling;
- scheduled 24h/morning-of reminders and daily Hub countdown delivery;
- device test-push support.

The implementation branch reported **875 backend tests green** and a clean frontend TypeScript
check.

### Live deployment follow-up

This is no longer feature-development work, but it must be completed on the home server:

1. rebuild backend/frontend images and apply the notification migrations;
2. configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT`;
3. run `notifications_run_scheduled` at least hourly;
4. validate at least two users/devices with different preferences;
5. confirm sensitive sources do not leak protected lock-screen content;
6. confirm notification deep links re-check current permissions;
7. on iOS, test an **installed Home Screen PWA**, not an ordinary Safari tab.

Exact commands and operational notes are in `HANDOVER.md`.

---

## 3. Start here — production serving

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
- serve that static output from a small production web server or an appropriate proxy path;
- ensure SPA routes fall back correctly to `index.html`;
- preserve `/api/` routing to Django;
- verify PWA/service-worker and push behaviour from the final production build, not only `vite dev`.

### 3.3 Production Django settings

Confirm and deliberately select the live Django production settings rather than assuming the
switch happened because documentation recommends it.

At minimum verify:

- `DJANGO_SETTINGS_MODULE` is the intended production module;
- production `DEBUG` behaviour;
- `DJANGO_ALLOWED_HOSTS` includes the trusted HomeStack hostname;
- `DJANGO_CSRF_TRUSTED_ORIGINS=https://homestack.moosesoftwares.com`;
- secure session/CSRF cookie behaviour works through NPM;
- secure-proxy handling matches NPM;
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
```

What needs to happen:

- establish an explicit shared Docker network between NPM and the HomeStack ingress services;
- make PostgreSQL internal-only in the production profile;
- remove unnecessary production host publication of `5432`, `8000` and `5173` once NPM can reach
  the appropriate containers directly;
- keep development-only port publication in a development override;
- keep NPM admin port `81` LAN/admin-only;
- do not introduce router port forwarding.

### Done when

A normal household client reaches HomeStack through the trusted HTTPS origin while database and
internal application ports are no longer generally exposed to the LAN in the production profile.

---

## 5. Create one supported deployment command

The current manual update sequence is easy to perform incorrectly. HomeStack has already reached a
stage where forgetting an image rebuild or migration can break the live household system.

Create one supported command, for example:

```bash
./scripts/deploy.sh
```

The deployment workflow should perform:

1. preflight checks;
2. verify/offer a current backup before risky changes;
3. build production backend/frontend images;
4. run database migrations safely;
5. recreate/restart services;
6. verify container health;
7. verify backend health endpoint;
8. verify the trusted HTTPS frontend/API origin;
9. verify required scheduled services/commands;
10. show deployed HomeStack version/commit;
11. give clear failure/rollback guidance.

The script must fail loudly after a failed migration or failed health check rather than reporting
success.

### Done when

A routine HomeStack update no longer requires remembering a multi-command sequence from the
Handover. One documented command performs the supported production deployment and verifies the
result.

---

## 6. Add frontend testing and CI

The backend has strong automated coverage. The next QA gap is the frontend and full browser flow.
The objective is not thousands of UI tests; it is protection for workflows that could make the
household system unusable if they regress.

Recommended stack:

- **Vitest** for frontend unit/component tests;
- **React Testing Library** for user-visible component behaviour;
- **Playwright** for a small number of complete browser flows;
- **GitHub Actions** for automated verification on pull requests.

Initial high-value browser flows:

- password login/logout;
- avatar/PIN login;
- sensitive re-authentication;
- Hub navigation;
- Calendar/source deep links;
- create/edit/complete an Atlas item;
- permission isolation between two users;
- Solace sensitive lock/re-auth behaviour;
- mobile navigation at a phone viewport;
- notification settings/device registration where practical;
- one representative write from another important domain.

Recommended CI checks:

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

What needs to happen:

- retain the existing database + protected-media backup contract;
- add at least one **encrypted copy off the primary HomeStack server/storage device**;
- preferably keep another copy in a different physical failure domain later;
- keep backup credentials/encryption keys outside ordinary user-facing configuration and outside
  the repository;
- record last successful local and off-server backup status;
- retain checksums/integrity validation;
- periodically perform an actual restore test;
- keep `docs/restore.md` aligned with the real supported process.

### Done when

Loss of the HomeStack server or its primary storage does not imply loss of the household database
and attachments, and a recent backup has been successfully restored in a real test.

---

## 8. Add an operational System Health surface

Once deployment and backup jobs are dependable, HomeStack should be able to tell an administrator
whether its own essential operational functions are healthy without requiring routine log reading.

Recommended Admin → **System Health** information:

- installed HomeStack version/commit;
- backend/database health;
- available storage/disk warning state;
- last successful local/off-server backup;
- last restore-test date where tracked;
- scheduled-command last-run/failure state;
- notification dispatcher status;
- Home Assistant bridge health once implemented;
- links to Uptime Kuma/Dozzle rather than rebuilding them.

Keep this intentionally small. HomeStack should expose the health of HomeStack, not become a full
server-monitoring replacement.

---

## 9. Stronger adult authentication before public remote access

LAN HTTPS is trusted, but HTTPS alone does not make HomeStack ready for public internet access.

Before any Cloudflare Tunnel or other public remote-access path is enabled, complete the security
gate in `05_Security_Architecture_Document.md`.

The recommended adult/admin improvement is **WebAuthn/passkeys or another strong second factor**
while retaining simple PIN login for ordinary LAN/kiosk use where appropriate.

Before public exposure:

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

Home Assistant remains the recommended next major integration after reliability work. Keep D22 and
`26_Node_Home_Assistant.md` intact:

- Home Assistant owns devices, state, history and automations;
- HomeStack owns People, permissions, household records and presentation mappings;
- backend-only HA token;
- explicit entity/control allowlists;
- read-only status first;
- safe low-risk controls second;
- no generic integrations framework.

### 10.2 Hearth / meal planning

Hearth remains a strong everyday domain:

- recipes;
- meal plans;
- dinner/weekly meal view;
- recipe import;
- ingredient scaling;
- send missing ingredients into the existing **Atlas Grocery** list.

Do not create another grocery/shopping data store.

### 10.3 Documents browser

The shared attachment system already provides the security/storage foundation. A future first-class
Documents surface can improve discoverability across manuals, receipts, insurance, school files,
pet records, warranties and contracts while preserving the owning domain record as source of truth.

### 10.4 Travel finishing work

Finish useful existing Travel slices rather than create another domain:

- packing lists;
- protected travel documents;
- later optional photo/journal/map/flight enrichments where they provide real value.

### 10.5 Health remains later

Do not rush medical Health. It raises the highest privacy/sensitivity bar in the product.
Production serving, reliable backups and stronger adult authentication should mature first.
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

---

## 12. Recommended delivery order

```text
COMPLETED
  Web Push / PWA notifications
        |
        v
LIVE ROLLOUT FOLLOW-UP
  VAPID + migrations + hourly dispatcher + real-device validation
        |
        v
CURRENT RECOMMENDED ENGINEERING PHASE
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

Some tasks can overlap, but this is the preferred priority order. Major new feature work should not
repeatedly displace production serving, deployment reliability and recovery.

---

## 13. Exit criteria for the reliability phase

HomeStack can reasonably be described as dependable household infrastructure when all of the
following are true:

- production Django server in use;
- production-built frontend in use;
- trusted LAN HTTPS verified for real authenticated reads/writes;
- PWA/Web Push verified from the production build on real household devices;
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

At that point, feature work such as Home Assistant and Hearth can proceed on a substantially more
dependable foundation.