# Recommended Next Steps — Production Readiness & Reliability

> **Status:** Recommended execution plan after completion of the PWA/Web Push implementation
> (v0.34.10–v0.34.13).
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
2. ~~**Production-serving and deployment hardening.**~~ — done, v0.35.0 (§3).
3. **Tighten container/network exposure — current phase.**
4. **Automate deployment and smoke validation.**
5. **Add frontend/E2E testing and CI.**
6. **Strengthen backup/recovery and operational health.**
7. **Add stronger adult authentication before any public remote-access plan.**
8. Then return to feature expansion such as Home Assistant, Hearth and later Health.

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
- device test-push support.

The implementation branch reported **875 backend tests green** and a clean frontend TypeScript
check.

### Live deployment follow-up

This is operational rollout, not unfinished feature development:

1. rebuild backend/frontend images and apply notification migrations;
2. configure `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY` and `VAPID_SUBJECT`;
3. run `notifications_run_scheduled` at least hourly;
4. validate at least two users/devices with different preferences;
5. confirm quiet hours and the fixed 24h/morning/countdown behaviour;
6. confirm sensitive sources cannot leak protected lock-screen content;
7. confirm notification deep links re-check current permissions;
8. on iOS, test an **installed Home Screen PWA**, not an ordinary Safari tab.

Exact commands are in `HANDOVER.md`.

---

## 3. Production serving — **completed (v0.35.0)**

> Implemented and validated locally; canonical detail now lives in
> `35_Production_Serving_and_Deployment.md`, which also carries the deployment, smoke-test and
> rollback procedures. The section below is retained as the original plan and its outcome.
>
> Delivered: gunicorn for Django; `npm ci` + `npm run build` served from nginx with SPA fallback;
> WhiteNoise for Django admin static; production/development Compose separation with
> `DJANGO_SETTINGS_MODULE` pinned per profile; production deployment system checks.
>
> Deliberately unchanged: published host ports and Nginx Proxy Manager configuration, so the
> change can be rolled back by rebuilding the previous commit. **§4 below is now the next step.**

Target shape:

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

### 3.1 Backend

Replace `runserver` in the live profile with a production WSGI server such as Gunicorn.

What needs to happen:

- add the production WSGI dependency;
- define a production container command;
- use sensible worker/timeouts for the small household workload;
- preserve health checks and useful logs;
- validate proxy headers and secure-cookie behaviour behind NPM;
- retain development `runserver`/reload in the development override.

### 3.2 Frontend

Stop serving the live application through Vite dev server.

What needs to happen:

- `npm ci` + `npm run build` in a build stage;
- serve the resulting `dist` from a small production web server/proxy path;
- support SPA fallback to `index.html`;
- preserve `/api/` routing;
- verify service-worker/PWA/Web Push from the production build.

### 3.3 Production Django settings

Verify deliberately rather than assuming:

- intended `DJANGO_SETTINGS_MODULE`;
- production `DEBUG` behaviour;
- allowed hosts and CSRF trusted origin;
- secure session/CSRF cookies behind NPM;
- proxy SSL handling;
- static/admin asset handling;
- secrets outside the repository.

### Done when

- no Django `runserver` in the live profile;
- no Vite dev server in the live profile;
- login/PIN/password re-auth work through HTTPS;
- an authenticated write succeeds through HTTPS;
- production PWA/Web Push still works;
- backend/frontend smoke checks pass after recreation.

---

## 4. Tighten Docker networking

The production profile should expose only what needs LAN ingress.

Target:

```text
LAN -> NPM :443 -> HomeStack web/API -> PostgreSQL
```

What needs to happen:

- shared Docker network between NPM and HomeStack ingress services;
- PostgreSQL internal-only;
- remove unnecessary production host publication of `5432`, `8000` and `5173` once NPM can reach
  the containers directly;
- keep development ports in a development override;
- keep NPM admin `81` LAN/admin-only;
- no router port forwarding.

### Done when

Household clients use the trusted HTTPS origin while database/internal app ports are not generally
reachable from the LAN.

---

## 5. Create one supported deployment command

Create something like:

```bash
./scripts/deploy.sh
```

It should perform:

1. preflight checks;
2. verify or create a current backup before risky work;
3. build production images;
4. run migrations;
5. recreate/restart services;
6. verify container health;
7. verify backend and HTTPS frontend/API health;
8. verify required scheduled jobs/configuration;
9. display deployed version/commit;
10. provide clear failure/rollback guidance.

The command must fail loudly after a failed migration/health check.

### Done when

A routine deployment no longer depends on remembering a multi-command handover sequence.

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

### Done when

A PR cannot silently break migration state, the production frontend build or critical household
browser flows without CI reporting it.

---

## 7. Strengthen backups and recovery

HomeStack contains important household data. A backup on the same server/storage device is not
enough long term.

What needs to happen:

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

- production serving;
- reduced service exposure;
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
COMPLETED — LIVE ROLLOUT
  VAPID + migrations + hourly dispatcher + real-device validation
        |
        v
COMPLETED (v0.35.0)
  Production Django + production frontend
        |
        v
CURRENT ENGINEERING PHASE
  Tighter Docker networking
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

- production Django and frontend serving are in use;
- trusted HTTPS works for real authenticated reads/writes;
- PWA/Web Push works from the production build on real household devices;
- unnecessary development/database ports are not exposed in production;
- one supported deployment command builds, migrates, restarts and smoke-tests;
- backend/migration/frontend/critical browser checks run automatically;
- at least one encrypted backup exists off the primary server/storage;
- restore has been successfully tested;
- administrators can see basic HomeStack operational health;
- stronger adult authentication exists before public access;
- the public-access gate remains closed until deliberately satisfied.