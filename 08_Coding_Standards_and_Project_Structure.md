# Document 8 — Coding Standards & Project Structure

> Canonical. Supersedes all earlier coding-standards docs. Decisions D1–D18 in
> `00_README_and_Changelog.md`.

## 1. Purpose

Defines how HomeStack code is organised and written so a solo developer can keep a broad
system maintainable, and so a future contributor (or buyer) can read it.

## 2. Repository structure

```
project-homestack/
  backend/
  frontend/
  docs/
  docker/
  scripts/          # backup/restore, data imports (Meridian/Solace migration)
  backups/
  .env.example
  docker-compose.yml
  docker-compose.dev.yml
  README.md
```

## 3. Backend structure

```
backend/
  config/ (settings/{base,dev,prod,test}.py, urls.py, asgi.py, wsgi.py)
  apps/
    core/  accounts/  people/  permissions/  nodes/  hub/  scheduling/
    notifications/  attachments/  audit/  search/  backups/  events/
    atlas/  home_wiki/  pets/  education/  inventory/  assets/  hearth/
    travel/  projects/  health/  meridian/  solace/
```
- `scheduling`, not `calendar` (D16).
- `events/` is the **thin signal interface** only (D4) — no broker, no event table.
- No `households` multi-tenant app and no `integrations` app (D1, D13).

## 4. Frontend structure

```
frontend/src/
  app/  api/  components/{ui,layout,feedback}/
  features/{auth,hub,scheduling,kiosk,atlas,homeWiki,pets,education,
            inventory,assets,hearth,travel,projects,health,meridian,solace,settings}/
  hooks/  theme/  types/  utils/
```

## 5. Documentation structure

```
docs/
  00_README_and_Changelog.md
  01_Master_Software_Specification.md
  02_Software_Architecture_Document.md
  03_UIUX_Design_Guide.md          # (file 07 in this set; renumber if you prefer)
  03_Database_Design_Document.md
  04_Development_Roadmap.md
  05_Security_Architecture_Document.md
  06_API_Specification.md
  08_Coding_Standards_and_Project_Structure.md
  09_Node_Model_Decision_Record.md
  10_Future_Features_Parking_Lot.md
  nodes/ (atlas, home-wiki, pets, education, inventory, assets, hearth,
          travel, projects, health, meridian, solace).md
```
This set is the single source of truth; archive all superseded `.docx` files.

## 6. Backend standards

Each Django app includes:
`models.py`, `serializers.py`, `views.py` (thin), `urls.py`, `permissions.py`, `services.py`
(business logic), `selectors.py` (read/query logic), `events.py` (signal publish/handlers),
`tasks.py` (scheduled/management-command work for now; Celery later), `tests/`.

Layering rules:
- **Views are thin** — they validate input and delegate.
- **Business logic in `services`**, read/query logic in `selectors`.
- **All models inherit `HouseholdBaseModel`** (Architecture §6): household scoping, soft
  delete, created/updated by **user**; subjects/assignees are **people** (D12).
- **Never bypass the central permission resolver.** Endpoints use it; selectors apply the
  visibility queryset mixin (D10). No ad-hoc permission checks in views.
- **Calendar via the scheduling helper only** (D7) — node code never writes `calendar_events`
  directly. Recurrence is one `recurrence_rule` (RRULE) on the owning record (D8).
- **Search via Postgres FTS** in selectors (D9) — no manual index maintenance.
- **Node decoupling via the `events` signal interface** (D4) — nodes never import each other's
  models.

## 7. Naming

Python `snake_case`; classes `PascalCase`; API routes lowercase kebab-case; DB fields
`snake_case`. Event names are clear state-change names: `pet_treatment_completed`,
`meal_plan_created`, `asset_maintenance_due`, `inventory_item_low`.

## 8. Node development checklist

Every node must provide: backend models (on the base model) · API endpoints · permissions via
the resolver · search integration (FTS) · calendar integration via the helper where applicable
· notifications where applicable · attachments via the shared service where applicable · event
signals · standard UI · mobile UI · kiosk UI where relevant · dark mode · tests · node doc.

## 9. Security checklist (per feature)

Who can view? Who can edit? Hub? Calendar? Search? Sensitive? Audit-logged? Re-auth needed?
Kiosk-allowed? Child-allowed? A feature isn't done until each is answered and enforced through
the central layer.

## 10. Testing standards

- **Permission tests first** — write them before the feature they protect (D10). This is the
  most important testing rule in the project.
- Unit tests for services/selectors; integration tests for the signal flows (e.g. Hearth →
  Inventory → Atlas) and for the scheduling helper's create/update/delete sync.
- Restore is tested: a backup can be taken and restored into a clean database (D17).
- Migrations are reviewed; data-import scripts (Meridian/Solace) have their own tests against
  sample exports.

## 11. Migrations & data-import standards

- Schema migrations are small and reversible where practical.
- Meridian/Solace imports live in `scripts/`, are idempotent where possible, map old data onto
  shared Users/People, and are dry-run-able before committing (D14).
