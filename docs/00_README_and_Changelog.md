# HomeStack Documentation — Index & Decisions

**Status:** canonical documentation index and architectural/product decision register.

**Last reconciled:** 2026-08-12

Historical release chronology is intentionally kept in `VERSION_HISTORY.md` and Git history rather
than duplicated here. `HANDOVER.md` describes only current operating/development state.

## 1. How the documentation is organised

### Current-state entry points

| File | Purpose |
|---|---|
| `../HANDOVER.md` | Read first when taking over coding work: current live state, hard rules, deployment, active work and known issues. |
| `00_README_and_Changelog.md` | This file: document map and settled decisions D1–D24. |
| `01_Master_Software_Specification.md` | What HomeStack is, current node model and stable product boundaries. |
| `04_Development_Roadmap.md` | Current sequencing, gates and genuinely future milestones. |
| `05_Security_Architecture_Document.md` | Authoritative authentication, permission, sensitivity, HTTPS and remote-access contract. |
| `34_Recommended_Next_Steps.md` | Practical recommended execution plan: finish Web Push, then production serving, deployment/network hardening, CI, backups and stronger operational readiness before major new feature expansion. |
| `VERSION_HISTORY.md` (repo root) | Historical feature/release chronology. |

### Architecture and implementation contracts

| File | Purpose |
|---|---|
| `02_Software_Architecture_Document.md` | Modular-monolith architecture, shared services and dependency boundaries. |
| `03_Database_Design_Document.md` | Data-model conventions and schema design. |
| `06_API_Specification.md` | REST/API conventions and contracts. |
| `07_UIUX_Design_Guide.md` | Responsive/kiosk/design/accessibility standards. |
| `08_Coding_Standards_and_Project_Structure.md` | App layering, coding and testing rules. |
| `09_Node_Model_Decision_Record.md` | Why domain boundaries exist and when a new node is justified. |
| `10_Future_Features_Parking_Lot.md` | Genuinely deferred ideas only. |

### Domain/core specifications

- `11_Node_Atlas.md`
- `12_Node_Home_Wiki.md`
- `13_Node_Pets.md`
- `14_Node_Education.md`
- `15_Node_Meridian.md`
- `16_Node_Inventory.md`
- `17_Node_Assets.md`
- `18_Node_Hearth.md`
- `19_Node_Travel.md`
- `20_Node_Projects.md`
- `21_Node_Health.md`
- `22_Node_Solace.md`
- `23_Core_Hub.md`
- `24_Core_Calendar.md`
- `25_Node_Homestead.md`
- `26_Node_Home_Assistant.md`
- `27_Node_Fitness.md`
- `28_Core_Corners.md`
- `29_Core_Link_Import.md`
- `30_Core_Daily_Coordination.md`
- `31_Core_Manage_HomeStack.md`
- `32_Core_Notifications_and_Push.md`
- `33_Node_Books.md` — shipped personal reading + shared Book Clubs node; added to the canonical
  set during the 2026-08-12 documentation reconciliation because the implementation existed but
  older node-model docs omitted it.

Milestone checklists remain useful as historical implementation/acceptance records but are not the
best source for current priorities. Current priorities come from `HANDOVER.md` and the Roadmap.

## 2. Source-of-truth precedence

When documentation conflicts:

1. an explicit newer owner decision beats older prose;
2. D1–D24 in this file define stable architectural/product boundaries;
3. the MSS/Security/Architecture/Database/Coding Standards define their respective contracts;
4. the relevant node/core specification defines domain behaviour;
5. `HANDOVER.md` defines current operational status and active work;
6. `VERSION_HISTORY.md`, milestone checklists and Git history are historical evidence, not current
   roadmap instructions.

Do not preserve a known contradiction merely because an old checklist/release entry says something
different.

## 3. Settled decisions

### D1 — One household per installation; keep household scope

HomeStack implements one household per self-hosted installation. User-facing models keep the
household relationship/base-model convention because it is structurally cheap and prevents later
schema pain, but SaaS-style tenant behaviour is not built.

### D2 — Self-hosted product model, not SaaS

If HomeStack is ever distributed to other families, they run their own instance. This avoids
HomeStack becoming custodian of many households' sensitive data and keeps product decisions aligned
with the current architecture.

### D3 — API-first clients

Business rules and permissions live in the backend API. Web, kiosk, PWA and any future native
client consume the same API rather than implementing separate business logic.

### D4 — Thin in-process events interface; no durable bus yet

Cross-domain notification/decoupling uses the shared Django-signal-based events interface. Do not
add an event table/broker/retry system until reliability/scale requirements prove it is needed.
Nodes do not couple by importing one another's models.

### D5 — Redis/Celery only when earned

Scheduled work currently uses management commands/host scheduling. Redis/Celery are not default
architecture and should be added only when the workload genuinely requires asynchronous workers or
reliable queued execution.

### D6 — Session auth, PIN convenience, password sensitive re-auth

Current web/kiosk auth uses Django sessions and avatar/PIN everyday login. Adult passwords protect
sensitive/admin elevation. PIN/password hashing uses Argon2id. Native token auth is deferred until a
native client needs it.

### D7 — Calendar has one source of truth

The owning domain stores the date/time/recurrence. Calendar projections are created/updated through
the shared scheduling helper and link back to the source. Nodes do not maintain competing Calendar
copies manually.

### D8 — One general recurrence representation

Recurring domain/event records use the established RRULE-style `recurrence_rule`. Do not invent
parallel repeat formats. D23 rotating layers are a bounded calculated schedule, not a second general
recurrence syntax.

### D9 — Search over permission-filtered owning data

Search uses Postgres full-text where applicable, with test-safe fallbacks, over each owning domain's
permission-filtered queryset. Do not maintain a second manually synchronized search-index database.

### D10 — Central backend permission resolution

Authorization and visibility are centralized. No ad-hoc view/button checks may become the security
boundary. Permission/security tests are written first for access-sensitive features.

### D11 — Shared attachment visibility/sensitivity model

Attachments use the shared visibility/sensitivity security contract; no parallel per-row ACL table
is introduced unless real requirements demonstrate that the current mechanism cannot express the
needed access.

### D12 — Users act; People are subjects

Audit/ownership/created-by/updated-by references Users. Assignment/subject relationships reference
People. People may exist without a login. Do not collapse the two concepts.

### D13 — Meridian and Solace are native HomeStack domains

They are not iframes or external-link integrations. Meridian moved early because it is family/kid
workflow; Solace followed security maturation because finance is sensitive.

### D14 — Rebuild shell/reuse proven behaviour; migration tooling is optional deployment support

Legacy Meridian/Solace behaviour informed the native implementations, but HomeStack uses its shared
Users/People/permissions/Calendar/etc. Data-import tooling can be dry-runnable/idempotent where
useful. For the live household Solace cutover, the owner chose fresh manual bill entry rather than
importing the old database.

### D15 — No household-specific schema/business rules

The installed household can configure its real people, pets, rooms and routines, but code/schema
must not assume this household's exact names/count/layout. The supplied house floor plan can seed
this installation's data/presentation without becoming a product-wide assumption.

### D16 — Calendar Django app is `scheduling`

Avoids collision with Python's standard-library `calendar` module.

### D17 — Backup means restore capability

A backup feature is incomplete without a documented, tested restore path and integrity checks.
Restore is treated as a first-class sensitive administrative operation.

### D18 — Walking skeleton/vertical delivery first

The project was deliberately built as complete usable vertical slices rather than laying empty
horizontal infrastructure for every imagined domain. Continue that approach for future work.

### D19 — Meridian is a full functional source-of-truth domain

HomeStack must support the real tasks/routines/points/rewards/approvals/goals/wishes/reporting
behaviour needed to replace standalone Meridian for household management, not a reduced demo subset.

### D20 — Achievements are cross-domain

Badges/achievement recognition are shared capability, with domains publishing events rather than
Meridian owning the entire concept. This allows Education/Fitness/etc. to participate without
cross-domain model imports.

### D21 — Homestead owns the home/property domain

Property, rooms, home maintenance, appliances, warranties, household services, home planning and
related home-specific context belong in Homestead. Financial ownership remains Solace where
appropriate. Future generic Assets does not duplicate the home scope.

### D22 — Home Assistant is a dedicated bounded bridge

Home Assistant owns devices, entities, areas, live state, recorder history and automations.
HomeStack owns household records, People, tasks, Calendar, permissions and presentation mappings.
The bridge is backend-only, allowlisted and permission/audit controlled. This does not authorize a
generic integrations/plugin framework.

### D23 — Rotating schedules are calculated cycles plus sparse exceptions

Alternating shared-care/shift/on-call-style schedules are stored as an anchored cycle and calculated
for the requested Calendar range. Individual changed days are sparse exceptions. Do not materialize
endless daily events.

### D24 — Fitness & Training is separate from medical Health

Fitness is a shipped social training domain for programs, workouts and records. Health is a future
sensitive medical domain. Diagnoses, medications, injuries, body measurements and medical notes do
not belong in Fitness.

## 4. Current high-level state

As of 2026-08-12 the live household installation includes the core platform, Meridian, Education,
Home Wiki, Pets, **Books**, Homestead, Solace/Money, Fitness & Training, Travel, Corners, safe link
import, Grocery/Shopping and the daily-coordination capabilities. Trusted LAN HTTPS is live at
`homestack.moosesoftwares.com` through Nginx Proxy Manager and Pi-hole.

The active implementation workstream is PWA/Web Push notifications. Home Assistant is intentionally
next only after that work is functioning. Public internet exposure is not enabled.

For exact current work and deployment commands, read `../HANDOVER.md`.

## 5. Documentation maintenance rule

When a feature ships:

1. update the owning node/core spec to describe the implemented contract;
2. update `VERSION_HISTORY.md` for release chronology;
3. remove it from `10_Future_Features_Parking_Lot.md` if it was parked;
4. update the Roadmap only if sequencing/status changed;
5. keep `HANDOVER.md` focused on current state rather than appending another permanent diary row.

This prevents the documentation set from accumulating multiple conflicting copies of the same
status.