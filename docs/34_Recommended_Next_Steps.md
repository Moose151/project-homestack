# Recommended Next Steps — Production Readiness & Reliability

> **Status:** Updated after the successful live production-serving rollout of v0.35.0 on
> **12 August 2026**.
>
> This document is practical guidance, not a replacement for the canonical Roadmap, Architecture
> or Security documents. It answers: **what should HomeStack do next, in what order, and what needs
> to be true before moving on?**

## 1. Recommendation

HomeStack has reached the point where the highest-value next phase is **not another large node**.
It already has broad household functionality, trusted LAN HTTPS, a PWA/Web Push layer and real daily
use. The next phase should make the application **dependable as household infrastructure**.

Recommended sequence:

1. ~~**Deploy and validate the completed Web Push work on the live server.**~~ — done, live.
2. ~~**Production-serving and deployment hardening.**~~ — done and live, v0.35.0 (§3).
3. **Tighten container/network exposure — current infrastructure phase.**
4. **Automate deployment and smoke validation.**
5. **Add frontend/E2E testing and CI.**
6. **Strengthen backup/recovery and operational health.**
7. **Add stronger adult authentication before any public remote-access plan.**
8. Then return to feature expansion such as Home Assistant, Hearth and later Health.

Small bug fixes and UI polish can continue in parallel where they do not change this reliability
sequence.

Reliability, recovery and repeatable updates now create more value than immediately adding another
major feature area.

---

## 2. Completed prerequisite — Web Push/PWA notifications

Canonical contract: `32_Core_Notifications_and_Push.md`.

Shipped behaviour includes:

- per-user category/channel preferences;
- per-user quiet hours and configurable morning time;
- per-device Web Push subscriptions;
- VAPID delivery;
- service-worker/PWA support;
- sparse sensitive-safe lock-screen payloads;
- permission/re-authentication checks after opening a deep link;
- expired/revoked subscription handling;
- household-activity bundling;
- fixed 24h/morning-of reminders for the bounded Calendar/Atlas scope;
- daily Hub countdown delivery;
- device test-push support;
- generated browser/platform device naming, user-editable friendly names and an admin household
  push-device overview.

The notification implementation is deployed on the live server. VAPID is configured, the hourly
scheduled dispatcher is active, existing push subscriptions survived the production-serving
transition, device registration/listing works from the production frontend, and real test pushes
were received successfully after the v0.35.0 rollout.

Longer-running behavioural validation such as quiet-hour timing and reminder timing should continue
through ordinary household use, but the rollout itself is complete.

---

## 3. Production serving — **completed and live (v0.35.0)**

Canonical detail: `35_Production_Serving_and_Deployment.md`.

The production-serving change was merged and deployed to the live home server on 12 August 2026.
The old Django development server and Vite development server are no longer in the live path.

Live shape:

```text
LAN client
    |
    v
Nginx Proxy Manager :443
    |
    +--> /api/* -> Gunicorn -> Django -> PostgreSQL
    |
    `--> /*     -> nginx -> production React/Vite build
```

Delivered:

- Gunicorn 26.0.0 serving `config.wsgi:application` on the backend;
- `gthread` worker model sized for the household workload;
- production React build produced with `npm ci` + `npm run build`;
- nginx serving the built frontend with SPA fallback;
- explicit caching rules for hashed assets, brand assets, the PWA manifest and `sw.js`;
- WhiteNoise 6.12.0 serving collected Django static/admin assets;
- production/development Compose separation;
- `DJANGO_SETTINGS_MODULE=config.settings.prod` pinned by the production Compose profile;
- production configuration checks for hosts, secrets, `DEBUG` and cookie/CSRF configuration;
- pre-promotion validation using throwaway containers from the newly built image;
- documented migration compatibility rule: backwards-compatible/additive migrations may run before
  promotion; destructive migrations require a brief planned backend outage;
- rollback procedure based on the known-good commit and image rebuild.

Deliberately unchanged in v0.35.0:

- Nginx Proxy Manager routing;
- host publication of PostgreSQL/backend/frontend ports;
- Docker network topology;
- router configuration.

### Live validation completed

The live deployment passed all of the following after promotion:

- backend and frontend container health checks;
- Gunicorn startup with three `gthread` workers;
- HTTPS backend health endpoint;
- HTTPS frontend load;
- password login and logout;
- avatar/PIN login;
- authenticated create/edit persistence;
- sensitive-node password re-authentication and Solace access;
- direct refresh of React deep links;
- `/sw.js` with `Cache-Control: no-cache`;
- `/manifest.json` with `application/manifest+json`;
- PWA brand assets;
- existing push-device listing and admin push-device view;
- real Web Push delivery from the production build;
- scheduled notification management command;
- no pending database migrations at deployment time.

The pre-deployment backup and rollback commit were also verified before promotion.

**§4 below is now the next infrastructure step.**

---

## 4. Tighten Docker networking — **current phase**

The production profile should expose only what needs LAN ingress.

Current live state intentionally retained from the pre-v0.35.0 deployment:

- PostgreSQL is published on host port `5432`;
- backend/Gunicorn is published on host port `8000`;
- frontend/nginx is published on host port `5173`;
- NPM reaches the application through those existing host ports;
- household users access HomeStack through `https://homestack.moosesoftwares.com`.

Target:

```text
LAN -> NPM :443 -> HomeStack web/API -> PostgreSQL
```

What needs to happen:

- create/use an appropriate shared Docker network between NPM and the HomeStack ingress services;
- make PostgreSQL internal-only in production;
- remove unnecessary production host publication of `5432`, `8000` and `5173` once NPM can reach
  the required containers directly;
- preserve explicit development port publication in the development override;
- verify NPM can still route `/api/*` to the backend and all other paths to the frontend;
- keep NPM admin `81` LAN/admin-only;
- keep HomeStack LAN-only;
- no router port forwarding.

Validation should include HTTPS login/PIN, an authenticated write, deep-link refresh, sensitive
re-authentication, PWA/service-worker loading and a real push test after the network change.

### Done when

Household clients use the trusted HTTPS origin while database/internal app ports are not generally
reachable from the LAN, and NPM reaches HomeStack only through the intended Docker-network paths.

---

## 5. Create one supported deployment command

Create something like:

```bash
./scripts/deploy.sh
```

The successful v0.35.0 manual rollout establishes the sequence this command should automate:

1. confirm a current, complete backup and record the known-good commit;
2. fetch/pull the intended release;
3. build production images without replacing the live containers;
4. run production configuration checks in a throwaway container from the **new** backend image;
5. inspect/apply migrations from the new image before promotion when migrations are backwards
   compatible;
6. stop the old backend before destructive/incompatible migrations when required;
7. promote the new containers only after checks/migrations succeed;
8. verify container health;
9. verify backend and HTTPS frontend/API health;
10. run deep-link/PWA/scheduled-job smoke checks;
11. display deployed version/commit;
12. provide clear failure/rollback guidance.

The command must fail loudly before promotion when configuration checks or migrations fail, and must
not silently continue after a failed health check.

### Done when

A routine deployment no longer depends on remembering the multi-command procedure proven during the
v0.35.0 rollout.

---

## 6. Add frontend testing and CI

Recommended stack:

- **Vitest**;
- **React Testing Library**;
- **Playwright**;
- **GitHub Actions**.

High-value browser flows:

- password login/logout;
- avatar/PIN login;
- sensitive re-authentication;
- Hub/navigation;
- Calendar/source deep links;
- Atlas create/edit/complete;
- permission isolation between two users;
- Solace sensitive lock/re-auth;
- phone-width navigation;
- notification settings/device registration where practical;
- one representative write from another important domain.

Recommended CI:

```text
backend tests
makemigrations --check
frontend typecheck
frontend unit tests
frontend production build
selected Playwright smoke tests
```

The production-serving PR finished with 908 backend tests, 907 green under the contributor's local
Python 3.14 environment, with the one remaining attachments test failure reproduced unchanged on
`main`. The live image is Python 3.12. CI should ultimately run in the supported project/runtime
version so local interpreter drift cannot obscure the real result.

### Done when

A PR cannot silently break migration state, the production frontend build or critical household
browser flows without CI reporting it.

---

## 7. Strengthen backups and recovery

HomeStack contains important household data. A backup on the same server/storage device is not
enough long term.

The v0.35.0 rollout verified that the existing backup service can create a complete PostgreSQL dump
plus media archive with checksums, and a pre-deployment copy was also made outside the Docker volume
on the host. That protects against a bad application deployment, but it does **not** protect against
loss of the server or its storage.

What still needs to happen:

- retain database + protected-media backup consistency;
- add at least one **encrypted copy off the primary server/storage device**;
- keep backup credentials/keys outside the repository;
- retain integrity/checksum verification;
- record last successful local/off-server backup where useful;
- periodically perform a real restore test;
- keep `docs/restore.md` aligned with the real process.

### Done when

Loss of the HomeStack server/primary storage does not imply loss of household data and a recent
backup has been successfully restored in a real test.

---

## 8. Add small operational health visibility

A future Admin → **System Health** surface should show HomeStack's own health, not replace Uptime
Kuma/Dozzle.

Useful data:

- installed version/commit;
- backend/database health;
- disk/storage warning state;
- last local/off-server backup;
- scheduled-command last-run/failure state;
- notification dispatcher status;
- Home Assistant health once implemented;
- links to existing operations tools.

---

## 9. Stronger adult authentication before public access

Trusted LAN HTTPS does not make HomeStack internet-ready.

Before Cloudflare Tunnel or other public remote access, satisfy
`05_Security_Architecture_Document.md`, including:

- production serving — **complete**;
- reduced service exposure — **next infrastructure phase**;
- strong adult/admin passwords;
- rate limiting/brute-force protection;
- passkeys/2FA or another strong second factor for privileged remote access;
- sensitive-node re-auth verification;
- secure proxy/cookie configuration;
- encrypted off-server backups;
- explicit threat-model/security review.

VPN-only remote access may still be preferable. Do not add router port forwarding as a shortcut.

---

## 10. Feature work after reliability

### Home Assistant

Next major integration after the reliability baseline. Preserve D22:

- HA owns devices/state/history/automations;
- HomeStack owns household records/People/permissions/presentation mappings;
- backend-only token;
- explicit allowlists;
- read-only status first;
- safe controls second;
- no generic integrations framework.

### Hearth

Recipes and meal planning should send missing ingredients into **Atlas Grocery**, not create a
second grocery data store.

### Documents browser

A central permission-aware discovery surface can aggregate shared attachments while keeping each
file linked to its owning domain record. OCR remains later.

### Travel

Prefer finishing packing lists/protected travel documents before inventing another domain.

### Health

Keep medical Health later. Production operation, recovery and stronger adult authentication should
mature before introducing the highest-sensitivity domain. Fitness remains separate under D24.

---

## 11. Infrastructure to keep deferred

Do not add without demonstrated need:

- Redis/Celery;
- microservices/Kubernetes;
- durable event broker;
- generic plugin/integration marketplace;
- generic automation engine;
- AI features without a clear household workflow.

The Django modular monolith remains appropriate. Improve its operation before replacing it.

---

## 12. Recommended delivery order

```text
COMPLETED
  Web Push / PWA implementation
        |
        v
COMPLETED — LIVE
  VAPID + hourly dispatcher + real-device push validation
        |
        v
COMPLETED — LIVE (v0.35.0, 12 Aug 2026)
  Gunicorn backend + built React/nginx frontend + production checks
        |
        v
CURRENT ENGINEERING PHASE
  Tighter Docker/network exposure
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
  System Health visibility
        |
        v
  Passkeys/2FA + remote-access security gate
        |
        v
FEATURE EXPANSION
  Home Assistant / Hearth / Documents / Travel finishing
        |
        v
LATER
  Health
```

## 13. Reliability-phase exit criteria

HomeStack can reasonably be treated as dependable household infrastructure when:

- [x] production Django and frontend serving are in use;
- [x] trusted HTTPS works for real authenticated reads/writes;
- [x] PWA/Web Push works from the production build on a real household device;
- [ ] unnecessary development/database ports are not exposed in production;
- [ ] one supported deployment command builds, validates, migrates, promotes and smoke-tests;
- [ ] backend/migration/frontend/critical browser checks run automatically;
- [ ] at least one encrypted backup exists off the primary server/storage;
- [ ] restore has been successfully tested;
- [ ] administrators can see basic HomeStack operational health;
- [ ] stronger adult authentication exists before public access;
- [x] the public-access gate remains closed until deliberately satisfied.
