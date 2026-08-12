# Document 8 — Coding Standards & Project Structure

> **Canonical implementation standards.** Decisions D1–D24 live in
> `00_README_and_Changelog.md`. These rules are intended for both human and AI contributors.

## 1. Purpose

Keep a broad, fast-moving household application maintainable without turning it into a collection
of special cases. New code should make ownership, permissions, reads/writes and deployment effects
obvious to the next contributor.

## 2. Repository structure

Current high-level layout:

```text
project-homestack/
  backend/
  frontend/
  docs/
  scripts/
  brand/
  backups/
  docker-compose.yml
  docker-compose.dev.yml
  .env.example
  README.md
  HANDOVER.md
  VERSION_HISTORY.md
```

Do not assume every old planned-node directory/spec is an active product domain. Current domain
status comes from the MSS/Roadmap/Handover.

## 3. Backend architecture

HomeStack is a Django modular monolith.

Core/shared apps include the authentication/People/permissions/nodes/Hub/scheduling/notifications/
attachments/audit/search/backups/events spine plus genuinely shared capabilities.

Current domain apps include Atlas, Meridian, Education, Home Wiki, Pets, Homestead, Solace,
Fitness and Travel. Home Assistant/Hearth/Health and evidence-gated capabilities follow their
roadmap status.

Rules:

- `scheduling`, not `calendar` (D16).
- `events` is a thin in-process boundary (D4), not a broker/event table.
- no SaaS tenant-management app (D1/D2).
- no generic integrations app merely for Home Assistant (D22).
- Fitness is separate from medical Health (D24).

## 4. Backend app layering

A normal domain/core app uses the relevant subset of:

```text
models.py
serializers.py
selectors.py
services.py
views.py
urls.py
admin.py
permissions.py     # where app-specific declarations are genuinely needed
events.py
tasks.py / management/commands/
tests/
```

### Views

Views are thin request/response adapters. They authenticate/parse/validate the request, call
selectors/services and return the response. Do not put long business transitions or cross-domain
logic in views.

### Selectors

Selectors own reads/query construction and apply visibility/permission filtering before data is
serialized or aggregated.

### Services

Services own writes and business transitions. They stamp ownership/audit fields, coordinate
Calendar/event/notification side effects and keep multi-step writes transactional where required.

### Serializers

Serializers define transport validation/representation, not the main business process. Be careful
with DRF read-only behavior for implicit FK `*_id` fields; declare writable fields explicitly when
required and test create/PATCH behavior.

## 5. Household model conventions (D1/D12)

Normal user-facing records use `HouseholdBaseModel` unless there is a deliberate reason for a
catalogue/global row not to be household-owned.

- ownership/audit fields reference **Users**;
- subject/assignee relationships reference **People**;
- soft delete uses the shared model/manager conventions;
- do not hand-roll household filtering differently in each domain.

## 6. Permissions (D10)

Never make frontend hiding or an ad-hoc view conditional the security boundary.

- use the central resolver/permission classes;
- filter records in selectors through the shared visibility/sensitivity model;
- write permission/security tests first when adding a new protected operation;
- re-check source permission when data is exposed through Hub, Calendar, Search, Corners,
  notifications or attachments;
- sensitive resources may intentionally use not-found behavior to avoid existence disclosure.

## 7. Cross-domain dependencies (D4)

Nodes do not import other nodes' models to implement integrations.

Use:

- shared core services when the concept is truly core;
- D4 publish/consume events for decoupled reactions;
- stable source IDs/deep links for projections;
- explicit service boundaries where an approved cross-domain action needs stronger coordination.

Do not solve a one-off dependency by creating a generic integration/workflow framework.

## 8. Calendar/date rules (D7/D8/D23)

- owning domain record keeps its semantic date;
- use the scheduling helper for node-derived Calendar mirrors;
- do not directly edit a generated Calendar record as though it owns the date;
- recurrence uses the established `recurrence_rule`/RRULE representation;
- rotating two-state schedules use the D23 calculated-cycle model and sparse exceptions.

Test create, update, clear/delete and permission propagation for Calendar-linked records.

## 9. Search (D9)

Search runs over permission-filtered owning data.

- PostgreSQL FTS where useful;
- keep the established SQLite/test fallback when the backend suite runs on SQLite;
- do not introduce a manually synchronized universal search table;
- snippets are created only after filtering inaccessible records.

## 10. Attachments (D11)

Use the shared attachment capability.

- permission-check downloads;
- audit sensitive downloads;
- do not expose private files through a raw public media route;
- preserve owning record/linkage;
- do not add a second ACL scheme unless the canonical attachment model is explicitly changed.

## 11. Frontend standards

Frontend code should reuse:

- shared API client/types;
- shared UI components/forms/dialogs/status/feedback;
- global navigation/session state;
- shared colour/design tokens;
- stable routes/query parameters for deep links.

Avoid page-local copies of components or API behavior that already exist centrally.

Responsive priority:

1. phone workflow intentionally usable;
2. desktop efficient without becoming dense enterprise UI;
3. kiosk adaptation where relevant.

Management tables should normally become cards/stacked records on small screens rather than rely on
horizontal scrolling.

## 12. TypeScript/API client

- keep API response/write types close to the actual backend contract;
- update client methods/types in the same change as backend route/serializer changes;
- avoid `any` for domain objects when a stable interface is known;
- handle 401/403/404/validation/reauth-required paths deliberately;
- do not infer permission from navigation visibility alone.

## 13. Naming

- Python/functions/fields: `snake_case`.
- Classes/types/components: `PascalCase`.
- React hooks: `useSomething`.
- API route segments: existing lowercase/kebab conventions; follow the owning URL module.
- Events: namespaced/stable state-change names; do not encode UI wording as event type.

Avoid renaming stable concepts casually because deep links, migrations and cross-domain events may
refer to them.

## 14. Testing standards

### Backend

Required according to feature risk:

- model/service/selector behavior;
- permission/visibility tests;
- Calendar sync create/update/delete/clear;
- event side effects and deduplication/idempotency;
- sensitive re-auth/audit behavior;
- regression tests for bugs found in live use;
- migration-drift check.

The main fast test suite may use SQLite while production uses PostgreSQL; PostgreSQL-specific code
must respect the established compatibility strategy.

### Frontend

Current production build/type checking remain required. The roadmap now explicitly calls for a
frontend automated test layer (unit/component plus a small Playwright critical-flow suite). New
front-end testing infrastructure should focus on high-value flows rather than broad snapshot noise.

### End-to-end / acceptance

Important cross-cutting flows deserve real browser/device validation: login/session, sensitive
reauth, Calendar/source deep links, push notifications, mobile navigation and critical household
writes.

## 15. Migrations

- Every schema change gets a new migration.
- Do not rewrite already-applied migrations to alter the live schema.
- Review migrations before deployment.
- Run `makemigrations --check` as part of verification/CI.
- Run `docker exec homestack-backend python manage.py migrate` after deploying a change containing
  migrations.
- Data migrations should be idempotent where practical.

## 16. Legacy/import tooling (D14)

Legacy Meridian/Solace import tools are operational utilities, not part of every deployment path.
They should remain dry-runnable/idempotent where appropriate and map into current HomeStack
Users/People/domain models.

The live household chose fresh manual Solace entry, so do not treat running the Solace importer as
an outstanding production milestone.

## 17. Background/scheduled work (D5)

Use scheduled management commands/host scheduling while that remains adequate.

Scheduled commands should be:

- idempotent or safely claim work;
- timezone-aware using the owning household timezone rather than relying on process-global UTC
  assumptions;
- bounded in work per run;
- observable enough to diagnose failures;
- safe to rerun after interruption.

Do not add Redis/Celery simply because a task is scheduled. Add them when queueing/retry/concurrency
requirements genuinely appear.

## 18. Security/secrets

Never commit:

- `.env`;
- database passwords;
- Django secret key;
- Cloudflare token;
- VAPID private keys;
- Home Assistant long-lived tokens;
- future offsite backup credentials/keys.

Do not log secrets or put them into API/audit metadata.

## 19. Deployment verification

For current base-compose deployments, code changes require image rebuilds. Migrations require an
explicit migrate step. After deployment verify both backend health and the trusted HTTPS origin.

The Roadmap includes replacing this manual process with a supported deploy script and production
serving profile.

## 20. Documentation maintenance

Do not append a permanent session diary to `HANDOVER.md`.

When work ships:

- update the owning node/core spec if its contract changed;
- update `VERSION_HISTORY.md` for release chronology;
- update MSS/Roadmap/Security only if their stable/current contract changed;
- remove shipped work from the Parking Lot;
- keep `HANDOVER.md` limited to current state, deployment, known issues and next work.

## 21. Definition of done for a feature

A feature is not done until the applicable items are handled:

- backend model/service/selector/API;
- permission/visibility/security behavior;
- Calendar/Hub/Search/Corners/notifications integration where relevant;
- responsive frontend flow;
- loading/empty/error feedback;
- dark/accessibility/touch behavior;
- automated tests appropriate to risk;
- migrations/operational command if needed;
- documentation/update note;
- deployment impact understood.

Prefer a smaller fully integrated feature over a larger half-wired one.