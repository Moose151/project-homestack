# Document 2 — Software Architecture Document (SAD)

> Canonical. Supersedes all earlier SAD versions. Decisions referenced as D1–D18 live in
> `00_README_and_Changelog.md`.

## 1. Purpose

Defines HomeStack's software architecture: a secure, API-first, modular household platform
built as a **modular monolith**, run self-hosted on a single always-on home server, for one
household. The architecture deliberately keeps a small number of future doors open (native
clients, a possible self-hosted product) while avoiding work that a single household does not
yet need.

## 2. Architectural style

**Modular monolith.** One Django backend, internally separated into apps with clean
boundaries. This gives the separation benefits of services without the operational cost of
microservices — the right fit for one developer and one server.

Cross-node communication uses **Django signals behind a thin internal event interface**
(D4), not a durable message bus. The interface is shaped so a real bus could replace it later
without touching node code, but no `event_bus_events` table, retry machinery or broker is
built for V1.

## 3. Technology stack

**Backend:** Python · Django · Django REST Framework · PostgreSQL.
*Redis and Celery are deferred (D5)* until a feature genuinely needs background processing;
early scheduled work (reminders) runs through a Django management command on cron.

**Frontend:** React · TypeScript · Vite · TailwindCSS · a shared component library.

**Deployment:** Docker Compose on a Linux home server. Local network first; reverse proxy /
HTTPS / VPN added before any remote access (see Security doc). No public exposure in early
scope.

**Mobile/desktop (later, undecided — D3):** the API-first design keeps React Native, Tauri/
Electron, or a PWA all viable. A solid PWA is the likely first bridge to phones. This choice
is deliberately deferred and does not block backend work.

## 4. High-level architecture

```
Clients:  Web app   ·   Kiosk UI        (later: PWA, native apps)
                 │
                 ▼
Backend (Django, modular monolith)
   ├─ Core services (accounts, people, permissions, scheduling, hub,
   │                 notifications, attachments, audit, search, backups, nodes)
   ├─ Node apps (atlas, home_wiki, pets, education, inventory, assets,
   │             hearth, travel, projects, health, meridian, solace)
   └─ Internal event interface (signals; swappable for a real bus later)
                 │
                 ▼
Storage:  PostgreSQL   ·   File storage volume   ·   Backup volume
          (Redis/Celery added only when needed)
```

## 5. Backend app structure

Core: `core`, `accounts`, `people`, `permissions`, `nodes`, `hub`, `scheduling`,
`notifications`, `attachments`, `audit`, `search`, `backups`, `events` *(thin signal
interface only)*.

Nodes: `atlas`, `home_wiki`, `pets`, `education`, `inventory`, `assets`, `hearth`, `travel`,
`projects`, `health`, `meridian`, `solace`.

Notes:
- The scheduling app is named **`scheduling`**, not `calendar`, to avoid colliding with
  Python's stdlib `calendar` module (D16).
- There is **no `households` app with multi-tenant behaviour**; a single household row is
  seeded at install. The tenant column is carried by the base model instead (§7, D1).
- Meridian and Solace are **first-class node apps** (D13), not under an `integrations` shell.
  No external-link/iframe layer is built.

```
backend/
  manage.py
  config/
    settings/ (base.py, dev.py, prod.py, test.py)
    urls.py  asgi.py  wsgi.py
  apps/
    core/  accounts/  people/  permissions/  nodes/  hub/  scheduling/
    notifications/  attachments/  audit/  search/  backups/  events/
    atlas/  home_wiki/  pets/  education/  inventory/  assets/  hearth/
    travel/  projects/  health/  meridian/  solace/
```

## 6. The base model (D1, D12, D17)

A shared abstract base model gives every user-facing table consistent behaviour and is the
mechanism that keeps the tenant column cheap to carry:

```python
class HouseholdBaseModel(models.Model):
    household    = models.ForeignKey("core.Household", on_delete=models.PROTECT)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    created_by   = models.ForeignKey("accounts.User", null=True, related_name="+", ...)
    updated_by   = models.ForeignKey("accounts.User", null=True, related_name="+", ...)
    deleted_at   = models.DateTimeField(null=True, blank=True)   # soft delete

    objects = HouseholdManager()   # default-filters to the active household, hides soft-deleted

    class Meta:
        abstract = True
```

- `created_by` / `updated_by` are **users** (ownership/audit). Record subjects/assignees are
  **people** via explicit `assigned_to_person` / `person` fields (D12).
- The default manager scopes to the single active household and excludes soft-deleted rows,
  so node code never has to remember either concern. If multi-household is ever wanted, the
  scoping already lives in one place.

## 7. Permissions architecture (D10)

Permissions are **resolved centrally**, not checked ad hoc per view. Two pieces:

1. **A permission resolver** — one function that, given (user, action, resource/node),
   returns allow/deny by combining: role, per-user overrides, node-enabled status, record
   visibility, sensitivity, and current re-auth state.
2. **A visibility queryset mixin** — applied in selectors so list endpoints only ever return
   rows the requester may see (filtered by household, role, visibility, sensitivity, re-auth).

Every endpoint passes through both. Permission tests are written **first**, before node
features, because this is the security spine and the part that becomes critical the moment
the app reaches families you don't know.

## 8. Scheduling (Calendar) architecture (D7, D8)

**Node records own their dates.** A single helper in the `scheduling` app creates, updates
and deletes `calendar_events` derived from node records, and stores the resulting
`calendar_event_id` back on the source row. Nodes call this helper on save/delete; they never
hand-write calendar rows. This removes the double-source-of-truth drift between, e.g., a pet
treatment's `next_due_at` and its calendar event.

**Recurrence is expressed once** as an RRULE-style rule on the owning record, and the helper
expands it for the calendar. No node keeps its own parallel `repeat_rule` format.

## 9. Search architecture (D9)

Search uses **PostgreSQL full-text search** (`tsvector` / `SearchVector`) over each node's
permission-filtered queryset, combined through the same visibility mixin as everything else.
No separately maintained `search_index` table to drift out of sync. OCR and semantic search
remain parked.

## 10. Attachments architecture (D11)

One shared attachments service. Access is controlled by `visibility` + `sensitivity` fields
on the attachment, reusing the central permission resolver. The per-row
`attachment_permissions` ACL table from earlier drafts is **deferred** — two permission
systems on one resource is a bug source. Sensitive downloads are audited.

## 11. Internal event interface (D4)

```python
# apps/events/bus.py  — thin, swappable
def publish(event_type: str, *, payload: dict): ...
def subscribe(event_type: str, handler): ...
```

Backed by Django signals for V1. Example flow (Hearth → Inventory → Atlas) is implemented as
signal handlers, synchronously, within a request or a scheduled command. If volume or
decoupling ever demands it, the same `publish/subscribe` surface can be re-pointed at Redis/
Celery or a real broker without changing callers.

## 12. Frontend structure

```
frontend/src/
  app/  api/  components/{ui,layout,feedback}/
  features/{auth,hub,scheduling,kiosk,atlas,homeWiki,pets,education,
            inventory,assets,hearth,travel,projects,health,meridian,solace,settings}/
  hooks/  theme/  types/  utils/
```

All nodes consume the shared component library; no node invents its own visual style (see
UI/UX doc).

## 13. API design

Base path `/api/v1/`. Groups mirror core services and nodes. Session auth for web/kiosk;
token auth added with native apps (D6). Full endpoint list lives in the API Specification.

Every endpoint validates, via the central layer: authentication, household ownership,
node-enabled status, role permission, record visibility, sensitive-node access, and
re-authentication where required.

## 14. Kiosk architecture

A dedicated frontend mode at `/kiosk` with states: ambient → avatar selection → PIN entry →
personal dashboard → node kiosk view → timeout return. Primary kiosk nodes: Hub, Calendar,
Atlas, Pets, Education, Hearth, Meridian. Restricted from the child kiosk by default: Solace,
Health, Assets, sensitive Documents, Settings.

## 15. Deployment architecture

Docker Compose services (V1):

- `homestack-backend` (Django/DRF)
- `homestack-frontend`
- `homestack-postgres`

Volumes: `postgres_data`, `media_data`, `backup_data`.

`homestack-redis` and `homestack-celery-*` are added only when a feature requires them (D5).
Access is local-network-only until HTTPS, a reverse proxy and the security checklist
(Security doc §14) are satisfied.

## 16. Backups & restore (D17)

Backup = `pg_dump` of the database **plus** a tarball of the media volume, recorded in the
`backups` table with checksum and status. **Restore is a defined, documented procedure**
(stop app or enter maintenance, `pg_restore`, unpack media, verify checksums, restart),
with expected downtime stated. Restore requires admin re-authentication. Restore is treated
as a first-class, tested feature, not an afterthought.

## 17. Build order (summary)

Foundation → Hub + Calendar → Atlas → native Meridian → Home Wiki + Pets + Education →
security maturation → native Solace → remaining nodes. Full detail and "done when" criteria
are in the Development Roadmap.

## 18. Meridian & Solace migration architecture (D13, D14)

Both are rebuilt as native node apps that use HomeStack's shared Users/People, scheduling,
attachments and permissions from day one. Their **proven business logic is reused** (reward/
points calculation; bill recurrence and payday-checklist behaviour); only the shell —
models, serializers, views — is rebuilt to fit the shared services. A **one-time import
script** migrates each app's live household data. No iframe/external-link integration is
built, since the destination is native. Meridian migrates early (no sensitive data); Solace
migrates after the security foundation is mature.
