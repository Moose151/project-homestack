# Document 2 — Software Architecture Document (SAD)

> **Canonical architecture contract.** Product decisions D1–D24 live in
> `00_README_and_Changelog.md`. Current deployment/work status lives in `HANDOVER.md`; historical
> implementation chronology lives in `VERSION_HISTORY.md`.

## 1. Architectural style

HomeStack is a **Django modular monolith** with one React frontend and one PostgreSQL database,
self-hosted for one household.

This is deliberate. Domain separation is enforced through app boundaries, shared services and
permission/event contracts without the operational cost of microservices.

Primary rules:

- one backend/API is the business-logic/security authority;
- nodes own their domain records;
- cross-node behaviour uses shared services and the thin events interface, not model imports;
- shared projections (Hub, Calendar, Search, Corners, notifications) do not become second sources
  of truth;
- Redis/Celery/durable brokers are added only when a measured workload requires them.

## 2. Technology stack

**Backend:** Python, Django, Django REST Framework, PostgreSQL.

**Frontend:** React, TypeScript, Vite, TailwindCSS and shared UI primitives.

**Current deployment:** Docker Compose on the Linux home server. LAN clients use trusted HTTPS at
`homestack.moosesoftwares.com` through the existing Nginx Proxy Manager and Pi-hole local DNS.
Public internet exposure is not enabled.

**Current live-serving caveat:** the container definitions still launch Django `runserver` and the
Vite development server. A production-serving profile (production WSGI + built/static frontend)
and tighter private container networking are explicit near-term hardening work, not a reason to
redesign the application architecture.

**Background jobs:** scheduled Django management commands/host scheduling. Redis/Celery are
explicitly deferred (D5).

**Future clients:** PWA is the first phone bridge; native Android/iOS/desktop technology remains
undecided until the product demonstrates a real need beyond the responsive/PWA client (D3).

## 3. High-level architecture

```text
Clients
  responsive web / kiosk / PWA (native later if justified)
        |
        v
LAN TLS + reverse proxy
  Nginx Proxy Manager
        |
        v
HomeStack frontend
        |
        v
Django / DRF modular monolith
  Core services
    accounts, people, permissions, nodes, hub, scheduling,
    notifications, attachments, audit, search, backups, events
  Domain apps
    atlas, meridian, education, home_wiki, pets, homestead,
    solace, fitness, travel
  Planned/deferred domain apps/specs
    hearth, health, home_assistant, inventory/assets/projects as evidence requires
        |
        v
PostgreSQL + protected media + backup storage
```

The repository may contain skeleton/spec artifacts for planned domains. Presence of a directory or
spec does not itself mean a top-level node is active; the MSS/Roadmap/Handover define current
product status.

## 4. Backend boundaries

### 4.1 Core platform apps

- `core` — household/settings foundation.
- `accounts` — authentication Users and login/admin account flows.
- `people` — household Person profiles.
- `permissions` — central role/per-user resolution and visibility rules.
- `nodes` — node/capability registry and household enablement.
- `hub` — configurable daily aggregation widgets.
- `scheduling` — Calendar/event projections and scheduling helpers (D7/D16).
- `notifications` — in-app notifications and the expanding Web Push delivery capability.
- `attachments` — protected shared files.
- `audit` — immutable security/administrative activity.
- `search` — permission-aware global aggregation.
- `backups` — database/media backup/restore records and services.
- `events` — thin in-process publish/subscribe boundary (D4).
- shared cross-domain capabilities such as achievements/link imports where their ownership is
  genuinely platform-wide.

### 4.2 Current domain apps

- `atlas`
- `meridian`
- `education`
- `home_wiki`
- `pets`
- `homestead`
- `solace`
- `fitness`
- `travel`

Home Assistant is a deliberate dedicated bridge when implemented; Hearth and Health are future
major domains. Inventory/Assets/Projects remain evidence/capability-gated rather than automatic
new navigation nodes.

### 4.3 Layering inside an app

Normal app structure follows the coding standards:

```text
models.py
serializers.py
selectors.py     # permission-filtered reads
services.py      # writes/business transitions
views.py         # thin request/response adaptation
urls.py
events.py / tasks.py where needed
tests/
```

Do not move business logic into React or duplicate permission logic in individual views.

## 5. Household base model (D1, D12)

User-facing domain records use the shared household-scoped base-model convention: household,
created/updated timestamps, created/updated Users and soft-delete support.

Conceptually:

```python
class HouseholdBaseModel(models.Model):
    household = models.ForeignKey("core.Household", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey("accounts.User", null=True, related_name="+", ...)
    updated_by = models.ForeignKey("accounts.User", null=True, related_name="+", ...)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = HouseholdManager()

    class Meta:
        abstract = True
```

`created_by`/`updated_by`/audit actors are Users. Record subjects/assignees are People (D12).

The household column is retained even though runtime behaviour is one household per installation;
it is not permission to implement SaaS tenancy.

## 6. Permissions architecture (D10)

Security is enforced centrally, not by frontend state or scattered per-view conditionals.

The permission spine combines:

- authentication/active-account state;
- household scope;
- role and per-user overrides;
- node/capability enablement;
- record visibility/sensitivity;
- child/kiosk restrictions;
- sensitive re-authentication where required.

Selectors apply visibility before serialization. Derived services (Hub/Search/Calendar/Corners/
notifications) must use the same source permission boundary rather than aggregate first and filter
later.

Permission/security tests precede feature behaviour where access boundaries change.

## 7. Scheduling / Calendar (D7, D8, D23)

**Owning records own dates.** Node/service records with dates sync into Calendar through the shared
`scheduling` helper. Calendar projections carry source identifiers/deep links and are maintained
from the owning data.

Do not hand-write a duplicate date into Calendar from a node service.

General recurrence uses the established RRULE-style `recurrence_rule` (D8).

Generic alternating two-state schedules are the bounded D23 exception: a `RotatingSchedule`
stores one anchored cycle and sparse date exceptions; selectors calculate only the requested
window. They do not materialise endless daily `CalendarEvent` rows.

Standalone Calendar-owned appointments/events remain valid owning records in `scheduling`.

## 8. Hub, Search, Corners and notifications are projections

These shared surfaces improve discoverability but do not own the underlying domain fact.

- **Hub** — widget selectors return permitted summaries/actions.
- **Search** — queries permission-filtered owning querysets; snippets are built only after
  filtering.
- **Corners** — person-centred activity/assignments/lists project owning records and preserve
  visibility/deep-link boundaries.
- **Notifications** — notification records/delivery link to source meaning but cannot bypass its
  permissions; Web Push payloads stay sparse for sensitive content.

Deleting/locking/changing visibility on a source record must not leave a derived surface that still
reveals it.

## 9. Search architecture (D9)

Use PostgreSQL full-text search where appropriate over each domain's permission-filtered queryset,
with SQLite/test-safe fallbacks where required by the test strategy.

Do not maintain a separately synchronized universal `search_index` table. OCR/semantic search are
future optional enrichments, not replacements for source permissions.

## 10. Attachments (D11)

Files use the shared attachment service and visibility/sensitivity permission model.

- protected downloads pass through application permission checks;
- sensitive downloads are audited;
- storage paths must not expose private files through an unauthenticated public media URL;
- node/domain records link to attachments rather than inventing independent file-security models.

A per-file ACL system is deferred unless real requirements outgrow the shared contract.

## 11. Internal events interface (D4)

Cross-domain reactions use a thin interface conceptually shaped as:

```python
publish(event_type, payload=...)
subscribe(event_type, handler)
```

The implementation is in-process Django signals. Synchronous handlers must fail safely and avoid
creating circular domain dependencies.

Do **not** introduce an `event_bus_events` table, retry broker or generic workflow engine merely for
architectural symmetry. If push/HA/other background workloads later prove signals insufficient,
change the implementation behind the boundary deliberately.

## 12. Frontend architecture

The React application is one product shell with shared navigation, authentication/session state,
API client, responsive components, feedback/error states and design tokens.

Domain pages/components should:

- call the shared API client;
- reuse shared UI primitives;
- work at phone/laptop sizes before bespoke kiosk polish unless the feature is kiosk-specific;
- treat backend permission failures/reauth-required responses as authoritative;
- keep route/query state stable enough for deep links from Calendar/Search/Corners/notifications.

The current Vite dev-server proxy can route `/api` during development. The planned production
profile should build static assets and let the reverse-proxy/application routing be explicit rather
than rely on a development server in production.

## 13. API architecture

Base path: `/api/v1/`.

The API is the contract for web/kiosk/PWA/future native clients. Endpoints should use consistent
error envelopes/status codes and keep write logic in services and read logic in selectors.

A client cannot gain authority by knowing an object ID, deep link or notification payload; each
request re-runs authentication/permission checks.

## 14. Kiosk architecture

Kiosk is a frontend mode over the same backend/security model, typically:

```text
ambient -> avatar -> PIN -> personal/kiosk dashboard -> permitted workflow -> timeout
```

Kiosk-safe APIs/widgets are deliberately constrained. Sensitive nodes are hidden by default and
remain backend-locked even if UI navigation is manipulated.

## 15. Current deployment architecture

Current household topology:

```text
LAN client
  -> Pi-hole: homestack.moosesoftwares.com -> 192.168.1.125
  -> Nginx Proxy Manager :443
       Let's Encrypt certificate via Cloudflare DNS challenge
  -> HomeStack frontend/backend containers
  -> PostgreSQL
```

HomeStack itself does not manage the Cloudflare DNS token; NPM owns that certificate credential.
No public router port forwarding is required for DNS-01 certificate issuance/renewal.

### 15.1 Near-term deployment hardening

The architecture target is:

- production WSGI server for Django;
- built/static frontend instead of Vite dev server;
- private Docker network between NPM/application/database where practical;
- PostgreSQL not exposed directly to the LAN;
- one supported deploy command that builds, migrates, restarts and smoke-tests safely.

Keep a development profile/override for hot reload and direct development ports.

## 16. Backups and restore (D17)

A HomeStack backup consists of database data plus protected media and integrity metadata. Restore is
a defined sensitive operation, not an afterthought.

Requirements:

- admin authorization and re-authentication for restore;
- checksums/integrity verification;
- documented stop/restore/restart procedure;
- periodic real restore testing;
- near-term encrypted off-server/off-primary-storage copy.

## 17. Legacy Meridian/Solace relationship (D13/D14)

Meridian and Solace are native HomeStack domains, not integrations.

Their proven behaviour informed the native implementation, while HomeStack rebuilt the shell around
shared Users/People/permissions/Calendar/attachments/audit.

Import tooling remains useful for repeatable migration scenarios, but import is not a mandatory
architectural step for every installation. The live household chose fresh manual entry for Solace
rather than importing its old database.

## 18. Home Assistant boundary (D22)

When the bridge is implemented:

- Home Assistant owns devices/entities/live state/history/areas/automations;
- HomeStack owns household records/People/tasks/Calendar/permissions/presentation mappings;
- HomeStack stores only selected mapping/control/event metadata;
- HA credentials are backend deployment secrets;
- reads/actions are allowlisted, permission-checked and bounded;
- HA failure cannot block unrelated HomeStack writes.

No generic `integrations` app, iframe or arbitrary HA service-call proxy is authorized by D22.

## 19. Architecture evolution rule

Before introducing a new infrastructure component or boundary, identify the concrete failure mode
in the current architecture that it solves. Prefer strengthening the existing modular-monolith,
permissions, scheduling, events and deployment contracts over adding parallel systems.

Current architectural priorities are operational maturity (production serving/network/deploy/
backup), Web Push delivery and then the bounded Home Assistant bridge — not a microservice rewrite.