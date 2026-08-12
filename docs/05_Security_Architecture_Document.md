# Document 5 — Security Architecture Document

> **Canonical security contract.** Decisions D1–D24 live in `00_README_and_Changelog.md`.
> Implementation/release chronology belongs in `VERSION_HISTORY.md`; this file defines the
> security boundaries that current and future work must preserve.

## 1. Purpose and threat model

HomeStack stores household finances, personal details, documents, children's information and may
later store medical data. Even as a single-household LAN application, its security model assumes:

- another household member may legitimately have fewer permissions;
- a child/shared kiosk must not inherit an adult's sensitive access;
- a stolen/observed PIN is not sufficient to unlock finance/health data;
- derived surfaces (Hub, Calendar, Search, notifications, Corners) can leak data unless they
  re-check the source permission boundary;
- backups can expose essentially the whole system;
- any future remote/public path materially raises the threat level.

Principles: least privilege, secure defaults, backend enforcement, defence in depth, auditability,
sensitive-data separation and explicit failure states.

## 2. Authentication (D6)

Current web/kiosk/PWA authentication uses Django sessions.

- Everyday login: avatar + PIN.
- Adults/admins also have passwords.
- PINs and passwords use Argon2id hashing.
- PIN is intentionally a convenience credential and is never the only gate for sensitive areas.
- Token/native-client authentication is deferred until a native client actually needs it.

### 2.1 Transport

The household LAN uses a browser-trusted HTTPS origin:

`https://homestack.moosesoftwares.com`

TLS terminates at the existing Nginx Proxy Manager. Pi-hole resolves the hostname locally to the
home server. The Let's Encrypt certificate is issued/renewed through Cloudflare DNS challenge, so
no public inbound port is required for certificate validation.

This solves trusted transport on the LAN. **It does not make HomeStack approved for public
internet exposure.**

## 3. Permissions (D10)

Authorization is backend-enforced through the central permission/visibility spine. Frontend
visibility is presentation only.

Resolution considers the relevant combination of:

- authenticated/active User;
- household;
- role;
- per-user overrides;
- enabled node/capability;
- record visibility;
- record sensitivity;
- child/kiosk restrictions;
- current sensitive re-auth state.

List/search/aggregation surfaces must filter before serializing or producing snippets. New domain
features write permission/security tests first where access boundaries are involved.

## 4. Users vs People (D12)

- **User** = authentication/ownership/audit actor.
- **Person** = household subject/assignee/profile.

`created_by`, `updated_by`, review/audit actors and login security reference Users.
Assignments/subjects normally reference People. A Person may have no login.

## 5. Sensitive areas

Default/high-sensitivity domains and capabilities include:

- Solace / Money;
- future Health;
- sensitive Documents/Attachments;
- backups and restore;
- account/permission administration;
- protected Homestead policy/account/financial context;
- Home Assistant credentials/configuration and any sensitive controls;
- selected People fields where their content warrants stronger restriction.

Fitness & Training is **not** medical Health. It may contain private workouts but must not become a
store for diagnoses, medications, injuries, body measurements or medical notes (D24).

## 6. Sensitive re-authentication

Sensitive areas use password re-authentication rather than PIN re-entry.

- Re-auth creates a short-lived elevated session state.
- The elevation expires; kiosk elevation is intentionally more cautious/shorter.
- Sensitive APIs return a machine-readable locked/re-auth-required contract rather than relying on
  client-side route hiding.
- Source permissions and re-auth state are checked again for sensitive downloads/actions.
- Child accounts do not gain sensitive access merely by knowing/observing an adult PIN.

## 7. Kiosk security

Required controls:

- automatic timeout back to avatar selection;
- explicit logout/exit;
- kiosk-safe endpoints/Hub widgets only;
- no finance/health/sensitive-document leakage in normal kiosk summaries;
- sensitive elevation requires password and uses a shorter timeout;
- server-side permissions remain authoritative if kiosk UI state is manipulated.

## 8. Derived-surface security

### 8.1 Calendar

Generated Calendar projections inherit/reconstruct the owning record's visibility/sensitivity.
Financial/private/health details must not become visible simply because a date is projected.

### 8.2 Hub

Widgets use permission-filtered selectors. Disabled/locked/unauthorized nodes must not reveal
counts, titles, amounts or meaningful snippets.

### 8.3 Search

Search operates over permission-filtered owning querysets. Sensitive results are excluded before
snippet generation. Deep links re-check permissions at the destination.

### 8.4 Corners/activity

Person-centred activity is a projection, not a bypass. Summaries/reactions/deep links remain within
the source record's current visibility.

### 8.5 Notifications and Web Push

The shipped Web Push layer preserves the in-app notification centre as source of truth.

Security requirements implemented/required by `32_Core_Notifications_and_Push.md` include:

- categorized notification creation respects the current User's channel preference;
- event-driven household activity re-fetches source records and checks visibility per recipient;
- push subscriptions are User-owned;
- normal push respects quiet hours;
- sources whose node currently requires sensitive re-authentication are automatically blocked from
  Web Push delivery regardless of category preference;
- payloads remain sparse;
- opening a push re-checks current session, permission and re-authentication state;
- VAPID private-key material stays server-side/deployment-only.

Push delivery is best-effort and cannot become a transactional dependency for the owning domain
write.

## 9. Attachments (D11)

Attachments use the shared visibility/sensitivity mechanism rather than a parallel per-row ACL
system.

- Download endpoints permission-check every request.
- Sensitive downloads are audited.
- Files are not exposed through a public static/media directory that bypasses application
  permissions.
- Kiosk/child access follows the owning record/security policy.

A finer per-file ACL is deferred until real use proves the shared model insufficient.

## 10. Audit

Security/administrative actions should produce immutable audit records where meaningful,
including:

- login success/failure;
- sensitive-node access/elevation;
- account/role/permission changes;
- node enable/disable changes;
- sensitive attachment downloads;
- backup creation/restore;
- reviewed Home Assistant controls when implemented.

Do not record secrets, passwords, tokens, VAPID private material or unnecessarily sensitive payload
content in audit metadata.

## 11. Backups (D17)

A backup is sensitive because it can contain nearly all household data.

Current HomeStack requirements:

- admin-only backup management;
- restore requires admin re-authentication;
- database/media integrity checks;
- a documented, tested restore path.

Near-term hardening target: maintain an **encrypted off-server/off-primary-storage copy** and
periodically prove it can be restored.

## 12. Home Assistant security boundary (D22)

When implemented:

- base URL and long-lived token are deployment secrets, not browser data or ordinary node settings;
- discovery/configuration is admin-only;
- only explicitly mapped entities are returned;
- action requests use stored server-side allowlists, never arbitrary browser-supplied HA
  domain/service/entity combinations;
- controls are centrally permission-checked and audited;
- locks, alarms, garage/cover access, cameras and safety-critical devices remain read-only/absent
  until separately reviewed;
- timeouts, response limits, TLS/URL validation and redaction are mandatory;
- HA outage/invalid token must degrade the bridge without blocking HomeStack.

Home Assistant remains the owner of devices/state/history/automations.

## 13. Current LAN HTTPS deployment

**Confirmed live 2026-08-12:** trusted HTTPS is available locally at
`homestack.moosesoftwares.com`.

Topology:

```text
LAN client
  -> Pi-hole DNS: homestack.moosesoftwares.com -> 192.168.1.125
  -> Nginx Proxy Manager :443 (Let's Encrypt via Cloudflare DNS challenge)
  -> HomeStack frontend/backend
```

No router port forwarding is required for DNS-01 issuance/renewal. Nginx Proxy Manager admin is
LAN/admin-only.

Confirmed during HTTPS rollout:

- local DNS resolution to `192.168.1.125`;
- valid Let's Encrypt certificate;
- frontend HTTP 200 through the HTTPS hostname;
- `/api/v1/health/` HTTP 200 through the HTTPS hostname.

### 13.1 Production serving (v0.35.0)

The live path is gunicorn for Django and a built React bundle served by nginx; NPM's routing and
the published ports are unchanged. `35_Production_Serving_and_Deployment.md` is canonical.

Security-relevant properties, verified against a running gunicorn container behind a TLS proxy
rather than assumed:

- `DEBUG=False` is hardcoded in production settings and cannot be re-enabled from `.env`;
- the session cookie is issued `HttpOnly; SameSite=Lax; Secure`;
- `SECURE_PROXY_SSL_HEADER` makes Django treat proxied requests as secure, so secure cookies are
  actually sent;
- a same-origin authenticated write succeeds; a write carrying a foreign `Origin` is rejected;
- sensitive-node password re-authentication is still demanded after the change;
- logout invalidates the session;
- WhiteNoise serves `STATIC_ROOT` only — uploads remain behind the permission-checked attachment
  download path (D11) and gain no static URL;
- gunicorn keeps its default `forwarded_allow_ips`, so it does not trust `X-Forwarded-*` from
  arbitrary LAN addresses;
- production deployment checks (`apps/core/checks.py`) fail `manage.py migrate` on a placeholder
  secret key, loopback-only allowed hosts, or `DEBUG` enabled.

Still verify/retain as deployment hygiene:

- repeat real login plus a state-changing request over HTTPS after each deployment;
- no accidental public router forwarding;
- no Content-Security-Policy on the frontend yet.

## 14. Public/remote access gate

HomeStack remains LAN-only. VPN can be used for controlled remote access. Public reachability
(including Cloudflare Tunnel) is a **separate security milestone**.

Do not approve public exposure until all of the following are satisfied and reviewed together:

- [x] browser-trusted HTTPS on the household hostname;
- [x] central backend permission model;
- [x] sensitive-node password re-authentication;
- [x] protected attachment/download path;
- [x] audit coverage for sensitive/admin operations;
- [x] tested local backup/restore capability;
- [x] Web Push sensitive-source lock-screen protection;
- [x] production application serving (gunicorn + built static frontend; no `runserver` / Vite dev
      server in the live path — `35_Production_Serving_and_Deployment.md`);
- [ ] unnecessary direct host/container ports removed/restricted;
- [ ] secure-cookie/proxy production settings verified live;
- [ ] brute-force/rate-limit protections reviewed for login/re-auth endpoints;
- [ ] 2FA/passkey or equivalent stronger adult/admin remote authentication available;
- [ ] encrypted off-server backup/recovery path in place and restore-tested;
- [ ] explicit remote-exposure threat-model/review completed.

Even after the checklist is complete, VPN-only access may remain preferred.

## 15. Secret handling

Secrets must not be committed to Git or exposed to frontend bundles/logs.

Examples:

- database credentials;
- Django secret key;
- Cloudflare DNS API token (stored in Nginx Proxy Manager for DNS-01, not HomeStack `.env`);
- **VAPID private key** for the shipped Web Push service;
- future Home Assistant token;
- future offsite-backup credentials/encryption keys.

Use restricted provider tokens where possible and scope them only to the required resource/action.

## 16. Deferred security mechanisms

Deferred unless the threat model or implementation requires them:

- native-app token-auth hardening;
- field-level/database encryption beyond protected storage/access;
- per-file ACL tables;
- durable event-broker security;
- generic integration credential framework.

2FA/passkeys are no longer merely a generic future idea: they are a specific gate for public
remote access.

## 17. Security acceptance rule

A feature that displays, aggregates, notifies about, exports or downloads a record must be tested
against the **source record's access boundary**, not just the feature's route/button visibility.

Security regressions in derived surfaces are release blockers even if the owning node's direct API
remains correctly protected.