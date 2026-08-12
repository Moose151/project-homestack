# Document 3 — Database Design Document

> **Canonical database-design contract.** The exact physical schema is defined by the current
> Django models and migrations. This document defines the stable modelling conventions and domain
> ownership rules; it must not become a second manually maintained copy of every model field.

## 1. Database role

HomeStack uses PostgreSQL as the durable source of truth for one self-hosted household. The schema
supports shared platform services plus independently owned household domains inside one modular
monolith.

The database design prioritizes:

- one owning record for each household fact;
- household scoping and soft-delete consistency;
- clear User-versus-Person relationships;
- central visibility/sensitivity enforcement;
- source-linked Calendar/Hub/Search/notification projections;
- migrations as the authoritative physical-schema history.

## 2. Authoritative physical schema

When this document and code disagree about a concrete field/table/index, the authoritative order is:

1. applied/current Django migrations;
2. current Django models;
3. this document's modelling contract;
4. older milestone specs/checklists.

Do not copy hundreds of model fields into this document merely to mirror code. That caused previous
documentation drift as the product evolved quickly.

## 3. Household-scoped base model (D1/D12)

Normal user-facing records inherit the shared `HouseholdBaseModel` convention, providing the
household anchor, timestamps, created/updated Users and soft deletion.

Conceptually:

```python
household
created_at
updated_at
created_by       # User
updated_by       # User
deleted_at
```

The default manager hides soft-deleted rows and provides the single-household scoping hook.

Exceptions are deliberate global/catalogue rows where household ownership would be incorrect
(e.g. some static/global catalogues).

## 4. Users and People (D12)

The schema deliberately separates:

- **User** — login/authentication identity and audit actor;
- **Person** — household subject/assignee/profile.

Rules:

- `created_by`, `updated_by`, reviewer, completer and audit actor fields point to Users;
- assignee/subject/profile relationships point to People;
- a Person may have no linked User;
- do not replace Person relationships with Users merely because current household members happen
  to have accounts.

Some genuinely login-personal records can correctly reference a User rather than a Person. Books is
an example: `PersonalBookEntry` and `BookRating` represent one login User's own reading state/rating,
while household work/subject records continue to use People.

## 5. Visibility and sensitivity

Domain records that can be restricted use the shared visibility/sensitivity model defined by the
permission architecture. The exact fields/enums are owned by the corresponding mixins/models.

Derived records/surfaces must not weaken this boundary. In particular:

- Calendar source projections carry enough ownership/security metadata to filter correctly;
- attachment access is permission-checked at download time;
- Search/Hub/Corners/notifications query the owning data through permission-aware selectors;
- sensitive derived content is not duplicated into an easier-to-access table.

Membership/relationship constraints can add to the central permission boundary. For example, Books
club records are query-filtered to clubs the current User belongs to.

## 6. Calendar/source ownership (D7/D8/D23)

### 6.1 Node-owned dates

The domain record owns its semantic date/time and recurrence. Where a Calendar mirror is required,
the shared scheduling helper creates/updates/removes the corresponding `CalendarEvent` projection
and preserves source linkage.

Do not create a second editable copy of a node date in Calendar.

### 6.2 Standalone Calendar records

Calendar-owned appointments/events are valid first-class records in `scheduling`; these are their
own source of truth rather than projections from another domain.

### 6.3 Recurrence

General recurrence uses the established RRULE-style `recurrence_rule` representation.

### 6.4 Rotating schedules (D23)

Generic two-state alternating schedules are calculated from one anchored cycle plus sparse
exceptions. They do not materialize one database row per future day.

Not every node needs Calendar data. Books, for example, currently owns reading state and club
queues without inventing dates merely to appear on Calendar.

## 7. Core data families

The current database includes the following platform-owned families (exact models live in code):

- household/settings;
- Users/authentication;
- People;
- roles/permissions/per-user overrides;
- node/capability registry and household enablement;
- Hub widget configuration;
- scheduling/Calendar and rotating schedules;
- notifications;
- attachments;
- audit logs;
- backup records;
- shared achievements where cross-domain;
- safe link-import/cache/watch data where cross-domain.

These are shared services. Domain apps should not re-create parallel role, notification, file,
calendar or audit systems.

## 8. Current domain-owned data families

### Atlas

Owns household notes/lists/items/reminders and the shared Grocery/Shopping list records. Dated work
can project to Calendar. Atlas remains the owner even when an item appears in Agenda, Hub, Search or
a Person's Corner.

### Meridian

Owns household task/routine/reward/economy workflows: tasks/completions, points ledger, reward
catalogue/requests, routines/streak-related state, goals/wishes and related settings/history.
Cross-domain achievements remain shared rather than Meridian-only where D20 applies.

### Education

Owns institutions, academic profiles/courses, assessments, class/timetable records, education
events and associated education notes/files where implemented.

### Home Wiki

Owns persistent household reference pages/categories and their presentation flags. Page revision
history remains future unless/until implemented in migrations.

### Pets

Owns pet profiles, treatments/care schedules, appointments and pet-specific records. Recurring due
work remains Pet-owned and syncs to Calendar rather than Calendar becoming the pet-treatment store.

### Books

Owns the shared household Book catalogue and reading/club state:

- `Book` — shared catalogue metadata;
- `BookRating` — unique User + Book rating/notes;
- `PersonalBookEntry` — unique User + Book personal reading state (Want to Read / Reading / Read);
- `BookClub` and `BookClubMembership` — shared clubs and explicit membership;
- `BookClubBook` — one Book's state/position within a club;
- `BookClubQueueItem` — ordered up-next queue over club-book entries.

Personal and club views intentionally reuse the same Book and User+Book rating rather than store
parallel metadata/ratings. Club selectors enforce membership. URL/ISBN enrichment comes through the
shared Link Import capability; it is not another durable book-catalogue source of truth.

### Homestead

Owns the home/property domain: property/rooms/areas, room plans, maintenance, appliances, service
providers, cover/cost context, pools/spas, utility usage and floor-plan association data. Finance
records remain Solace-owned when they are actual financial schedule/budget facts.

### Solace / Money

Owns finance: bills/occurrences, pay cycles, buckets/allocation, planned purchases and other
implemented Money records. Old standalone-Solace schema names should not be carried into this
specification if the native models have since changed.

### Fitness & Training

Owns exercise catalogue/custom exercises, programs, workout/session snapshots, session exercises/
sets and personal-record/history data. It must not absorb medical Health data (D24).

### Travel

Owns trips/ideas, participants/visibility choices, bookings/cost planning and itinerary/Things-to-do
records. Dated itinerary/book-by/trip information can project into Calendar but remains Travel-owned.

## 9. Planned/evidence-gated domain data

### Home Assistant (D22)

When implemented, persist only HomeStack's mapping/presentation/control/event configuration. Do not
mirror all Home Assistant entity state, attributes or recorder history into PostgreSQL.

Credentials remain deployment secrets, not database rows intended for ordinary API/UI access.

### Hearth

Future recipe/meal-plan data may be durable in Hearth. Generated shopping output should target the
existing Atlas Grocery data rather than introduce a parallel grocery database.

### Health

Future medical data is sensitive by default and remains separate from Fitness.

### Inventory / Assets / Projects

Do not create large new schema families merely because old design documents proposed them. Their
current status is capability/evidence-gated by the MSS/Roadmap. Add migrations only after the domain
boundary is approved by real product need.

## 10. Attachments and external enrichment

Attachments use the shared file/security capability rather than a unique attachment table per
node.

Important database rules:

- retain owning/source linkage;
- keep checksum/metadata needed for integrity and safe delivery;
- enforce visibility/sensitivity through application permissions;
- do not add an `attachment_permissions` ACL table unless the shared model proves insufficient;
- physical file storage is not made public merely because an attachment row exists.

External metadata preview/cache/watch records remain shared Link Import infrastructure. Once a User
confirms Book/product fields, the owning Books/Atlas/Homestead/etc. record becomes the durable source
of truth rather than continuously mirroring the external page.

## 11. Search (D9)

There is no separately synchronized universal `search_index` source of truth. Search is built from
permission-filtered live domain querysets, using PostgreSQL FTS where appropriate and test-safe
fallbacks where required.

Domain-specific FTS indexes/generated vectors may exist as implementation details; they do not
change record ownership. Books currently follows this pattern for title, author, genre, ISBN and
description.

## 12. Events (D4)

There is no required `event_bus_events` durability table. Cross-domain event delivery uses the thin
in-process events interface.

If a future broker/durable queue is introduced, its persistence is infrastructure delivery state,
not a new source of truth for the domain facts carried in events.

## 13. Backups (D17)

Backup records track backup state/metadata/integrity information while the actual backup contains
both database data and protected media as defined by the backup service.

Restore remains an administrative operation, not merely a model transition. Database design must
remain compatible with migration-based restoration/upgrades.

## 14. Migration rules

- Every schema change ships as a Django migration.
- Data migrations should be idempotent where practical and must respect the single-household
  structure.
- Do not edit an already-applied migration to change current production behaviour; add a new
  migration.
- Deployment must run `python manage.py migrate` after new migrations reach the server.
- CI/verification should include migration-drift checks (`makemigrations --check`).
- Import scripts for legacy apps are operational tools, not substitutes for migrations.

## 15. Testing implications

The automated backend suite may run against SQLite for speed while production uses PostgreSQL.
Code using PostgreSQL-specific search/functions must provide the established test-safe fallback or
an explicit PostgreSQL integration test path.

Do not weaken production constraints merely to satisfy SQLite.

## 16. Removed/deferred schema concepts

Unless a later explicit decision supersedes D1–D24, do not create:

- SaaS tenant/signup/billing schema;
- `event_bus_events` as a speculative durable bus;
- universal synchronized `search_index` table;
- generic `integrations`/`external_apps` ownership layer;
- parallel attachment ACL system;
- duplicate Calendar stores inside nodes;
- a database mirror of all Home Assistant state/history.

## 17. Documentation rule for schema

When a new model ships, update the owning domain specification if the model changes the domain
contract. Do **not** expand this document into a complete field-by-field generated schema copy.

For exact current columns/constraints/indexes, inspect Django models and migrations. This keeps the
design documentation stable while the physical schema continues to evolve safely.