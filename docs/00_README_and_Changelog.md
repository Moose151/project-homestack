# HomeStack Documentation — README & Changelog

**Status:** Canonical source of truth. This consolidated set supersedes all earlier
`.docx` files in the project, including the previous Doc 00 update pack and the original
standalone documents. Archive the old files; do not edit them further.

**Last revised:** 2026-08-11
**Owner:** Solo developer (single household: two adults, two children)
**Deployment target:** Always-on home server, self-hosted, Docker Compose.

---

## How this set is organised

| File | Purpose |
|------|---------|
| `00_README_and_Changelog.md` | This file. Decisions, supersession, version history. |
| `01_Master_Software_Specification.md` | Vision, node model, scope, V1 definition. |
| `02_Software_Architecture_Document.md` | Technical architecture and the decisions behind it. |
| `03_Database_Design_Document.md` | PostgreSQL schema, base-model pattern, table definitions. |
| `04_Development_Roadmap.md` | Revised build order tuned to a solo dev. |
| `05_Security_Architecture_Document.md` | Authentication, permissions and threat boundaries. |
| `06_API_Specification.md` | REST conventions and endpoint contracts. |
| `07_UIUX_Design_Guide.md` | Shared responsive, kiosk and accessibility standards. |
| `08_Coding_Standards_and_Project_Structure.md` | App layering, repository and testing rules. |
| `09_Node_Model_Decision_Record.md` | Node boundaries and justification. |
| `10_Future_Features_Parking_Lot.md` | Deferred ideas and promotion rules. |
| `11`–`22`, `25`–`27_Node_*.md` | Per-node specifications, including Homestead, Home Assistant and Fitness. |
| `23_Core_Hub.md` / `24_Core_Calendar.md` | Core aggregation and scheduling surface specs. |
| `28_Core_Corners.md` / `29_Core_Link_Import.md` | Household Corners and safe URL-import contracts. |
| `PARTNER_PILOT_READINESS.md` | Two-adult account setup, per-destination readiness and real-device acceptance gate. |

The node specifications cover Atlas, Home Wiki, Pets, Education, Inventory, Assets, Hearth,
Travel, Projects, Health, Meridian, Solace, Homestead and Home Assistant; where they conflict
with anything here, **this set wins**.

---

## Decisions baked into this revision

These were settled in planning and are now treated as the project's position. Each notes
*why*, so future-you remembers the reasoning.

### D1 — Single household, but keep the tenant column
HomeStack runs one household per installation. Multi-household *behaviour* (signup,
tenant isolation, billing) is **dropped**. However, every table keeps a `household_id`,
enforced through a shared base model and default manager, hardcoded to a single household
row. Reason: re-adding tenant scoping later touches every table and query — it is the one
piece of multi-tenancy that is brutal to retrofit and nearly free to carry. This keeps a
possible future self-hosted product viable without building for it now.

### D2 — Self-hosted is the productization model (if ever)
If HomeStack is ever sold, it ships as a self-hosted app other families run themselves
(à la Home Assistant / Nextcloud / Mealie), **not** SaaS. This means no multi-tenant
hosting, no custody of other families' data, far less burden. The sell ambition disciplines
which decisions are treated as one-way doors; it does **not** inflate V1.

### D3 — API-first preserved
All clients talk to one REST API. This keeps native apps and a possible PWA bridge open
without backend rework, and defers the mobile/desktop tech choice (React Native vs.
Tauri vs. PWA) until it actually matters.

### D4 — Defer the durable event bus
The previous `event_bus_events` table with status/retry/processed machinery is **not built
for V1**. Node decoupling is achieved with Django signals behind a thin internal interface,
so a real bus can be swapped in later if genuinely needed. Reason: it duplicates a message
queue for a single-household app.

### D5 — Defer Celery/Redis
Background processing is deferred until a feature genuinely needs it. Early reminders run
via a scheduled Django management command (cron). Reason: lighter to run and reason about;
the broker can be added when it earns its place.

### D6 — Session-based auth first
Web and kiosk use Django session auth with avatar + PIN. Token auth is added only when
native apps arrive. Sensitive re-authentication is defined explicitly (see Security doc):
re-auth uses the user's password (adults) rather than the low-entropy PIN.

### D7 — Calendar has one source of truth
Node records own their dates. A single helper generates and syncs `calendar_events` from
node records (storing `calendar_event_id` on the source row). Nodes never double-write
dates. Reason: eliminates drift between a treatment's `next_due_at` and its calendar event.

### D8 — One recurrence representation
Recurrence is expressed once, as an RRULE-style rule, shared by calendar events and any
recurring node record (treatments, maintenance). No parallel `repeat_rule` formats.
The bounded rotating-schedule exception in D23 is a two-state calendar layer rather than a
second general event-recurrence field.

### D9 — Search via PostgreSQL full-text
Search uses Postgres FTS (`tsvector`) over each node's permission-filtered queryset rather
than a separately maintained `search_index` table that can drift. OCR/semantic search stay
parked.

### D10 — Central permission resolution
One permission-resolution function plus a visibility-filtered queryset mixin enforce
access; checks are not scattered per view. Permission tests are written first. Reason: this
is the security spine, and it becomes non-negotiable the moment the app reaches families
you don't know.

### D11 — Attachments: one permission mechanism for V1
Attachments use `visibility` + `sensitivity` fields. The per-row `attachment_permissions`
ACL table is deferred. Reason: two overlapping permission systems on one resource invite bugs.

### D12 — People vs. Users rule
`created_by` / `updated_by` / ownership / audit always reference a **user**.
`assigned_to` / subject-of-a-record always references a **person**. People may exist without
a login; users always have one.

### D13 — Meridian native early; Solace native after security
Meridian (tasks/rewards, kid-facing, no sensitive data) becomes a native node early, right
after the foundation and Atlas. Solace (finance, sensitive) becomes native only after the
security foundation is mature. The iframe / external-link layer is **skipped entirely** —
no throwaway integration shell.

### D14 — Rebuild Meridian/Solace shell, reuse logic, migrate data
Their models/serializers/views are rebuilt fresh to use HomeStack's shared services; their
proven business logic is reused; a one-time import brings the household's live data across.

### D15 — No household specifics in schema or logic
Nothing is hardcoded to this household (e.g. no "support for at least two cats"). A future
buyer won't have the same pets, people, or layout. Everything stays general.

### D16 — Rename the `calendar` app
The Django app is named `scheduling` (not `calendar`) to avoid colliding with Python's
standard-library `calendar` module.

### D17 — Backups specify restore
Backups define the actual restore path (pg_dump + media tarball, documented procedure,
expected downtime), not just metadata. Restore is the riskiest operation and is treated as
a first-class feature.

### D18 — Walking skeleton first
The first milestone is a complete vertical slice (auth + People + Atlas + Hub + Calendar,
in Docker, with permissions and tests), used daily, before any other node is started.

### D19 — Meridian is a full functional port of the standalone app
The native Meridian node carries the **complete** feature set of the existing standalone app
(`~/Documents/new/project-meridian`): a signed points ledger (balance vs. lifetime "total
earned", reservation/refund), tasks with completion behaviours / recurrence / photo evidence /
assignment & scope / hot bonuses, a rewards shop with stock / daily limits / image carousel /
cart, routines with streaks, group goals, wishlist, allowance, separate task & reward
categories, reports / leaderboard / activity feed, and notifications. The earlier reduced M2
scope ("tasks · approvals · points · rewards · Hot Tasks · categories") is **superseded**.
Reason: the household uses the standalone app daily; a partial port is not a usable replacement,
and D14 ("reuse the proven logic") presupposes bringing the logic across, not a subset.

### D20 — Achievements/badges are a shared cross-node system
Badges live in a household-scoped, **cross-node** `achievements` app, not inside Meridian.
Nodes **publish events** (D4) and the achievements app consumes them and awards badges — no node
calls another node's models. The Hub surfaces a person's badges; any node (Education, Pets, …)
can register its own badges later with no Meridian changes. Meridian is the first producer
(seeding the 15 existing badges). Reason: recognition should span all of a child's activity, and
this keeps the awarding logic decoupled per D4/D10.

### D21 — Homestead is the home/property hub; it folds the *home* scope of Assets
The house domain (owner just bought a home, 2026-07-21) is delivered as one warm **Homestead**
node (spec `25_Node_Homestead.md`) rather than the coldly-named planned **Assets** node. Homestead
absorbs Assets' *home* scope — property record, home maintenance, appliances, warranties,
documents — plus house key-dates, a service-provider directory, and a lightweight improvements
list. The planned Projects node still owns heavyweight renovations; Homestead's Improvement carries
a dormant `project_ref` so an improvement can later link to a full Project. Homestead owns
home-specific policy/account context (insurance, rates, water, gas and other services), while
**Solace remains the financial calendar/budget mirror**. These protected Homestead records sync
linked Solace bills through events, never cross-node model imports (D4); financial Calendar rows
remain Solace-owned. A future Assets node may still cover non-home assets (vehicles, tools) or be
retired. Reason: matches how the owner thinks about "the house", keeps one daily surface, and
respects D4/D15.

### D22 — Home Assistant is a dedicated bridge node with strict source-of-truth boundaries
Home Assistant is an important planned opt-in node (spec `26_Node_Home_Assistant.md`, Roadmap
M5.5), not a generic integrations/plugin layer and not an iframe. **Home Assistant owns devices,
entities, areas, live state, recorder history and automations. HomeStack owns household records,
People, tasks, Calendar data, permissions, audit and presentation mappings.** HomeStack stores
only selected entity/action/event mappings; it does not mirror all entity state or history.
Integration is backend-only and REST-first, using a deployment-secret long-lived access token,
explicit entity/action allowlists, central permissions and audited controls. WebSocket state push
and a Home Assistant custom component are evidence-driven follow-ups, not V1 prerequisites. Other
nodes interact through the D4 event interface and continue working when Home Assistant is offline.
Reason: this creates useful smart-home visibility and automation without duplicate data entry,
unsafe generic service calls or another system of record.

### D23 — Rotating schedules use one cycle plus sparse date exceptions
Alternating two-state schedules such as shared care, shift work or on-call cover are stored once
as an anchored `P`/`S` cycle and expanded only for the Calendar range being viewed. They do
**not** create daily `CalendarEvent` rows. A changed day creates one
`RotatingScheduleException`; deleting it restores the calculated plan. The optional subjects are
People, while audit ownership remains Users (D12). This is a deliberately bounded Calendar
layer, not a new generic recurrence syntax and not household-specific custody logic (D8/D15).
Reason: an indefinitely forecastable multi-state cycle plus individual swaps is awkward and
fragile as multiple RRULEs, while one canonical cycle avoids repeated entry, drift and database
growth.

### D24 — Fitness is separate from medical Health
Fitness is a household-social training node for programs, workouts, activity and personal
records. Health remains a sensitive, password-gated medical node. Fitness sessions may be
household-visible or private but never contain diagnoses, medication, injuries, body measurements
or medical notes. Reason: combining social workout sharing with Health's strong sensitive-data
contract would either leak medical information or make ordinary training unusably locked down.

---

## Change history

| Date | Change |
|------|--------|
| 2026-08-11 | Shipped v0.31.0: household Corners aggregate permitted activity, assignments and source-owned lists; personal Atlas wish/shopping lists support suggestion review and grouped reactions; safe product-link previews enrich Atlas/Homestead items with local image caching and optional household-local daily price watches. |
| 2026-08-11 | Added Roadmap 8.2/8.3 and core specs 28/29: privacy-aware **Corners** (My Corner / Alex's Corner) aggregate activity, assignments and source-owned personal/room/Meridian lists; interaction uses suggestions plus bounded encouragement/comments/help offers. A shared preview-and-confirm URL importer enriches products and later Hearth recipes behind an explicit SSRF/security boundary; confirmed images cache locally and optional daily 09:00 household-local watches provide deduplicated sale/drop/target alerts without rewriting saved costs. |
| 2026-08-10 | Added D24 and shipped the Fitness & Training node: exercise library, multi-day programs, assignment, live editable workout logging, personal records, social notifications/history and responsive web UI. |
| 2026-08-09 | Prepared v0.21.0 for the controlled partner pilot: explicit per-user Money access during account onboarding; permission-aware node discovery, Hub widgets and Homestead finance actions; consistent mobile page hierarchy; responsive manager reward/allowance/goal/wishlist/routine workflows; labelled and failure-aware Books/Pets/Household guide forms; complete pet treatment/appointment management; and a canonical per-destination readiness/single-entry acceptance document. No database migration. |
| 2026-08-09 | Continued the UI overhaul in v0.20.4: Meridian manager tasks use responsive cards and inline labelled editing below desktop size instead of a horizontally scrolled table; task creation progressively reveals advanced fields; Atlas list items wrap with grouped assignment/due metadata; quick capture is progressive on phones; and rewards metrics use a more compact mobile hierarchy. No new architectural decision or database migration. |
| 2026-08-09 | Shipped the v0.20.3 app-style mobile Month view: the complete six-week grid is the edge-to-edge primary screen, occupied dates show compact coloured event labels, date details and actions open in a bottom sheet, and a floating add button plus Filter-hosted rotation management preserve calendar space. No new architectural decision or database migration. |
| 2026-08-09 | Shipped the v0.20.2 mobile Calendar redevelopment: in-place selected-day previews preserve Month context; swipes and safe month-end navigation accelerate forecasting; coloured event dots and the existing narrow care strip clarify the grid; view/filter controls and the 14-night rotation editor fit small screens; and the full monthly agenda is available without dominating the page. No new architectural decision or database migration. |
| 2026-08-09 | Shipped the v0.20.1 navigation and visual-system refinement: plain-language destination names with node brands as context, a purpose-grouped descriptive desktop sidebar, a complete mobile More directory with clearer bottom-bar editing, consistent shared headings/tabs, a non-duplicative widget-focused Hub and a calmer responsive Calendar toolbar. No new architectural decision or database migration. |
| 2026-08-09 | Added **D23** and shipped v0.20.0 rotating Calendar schedules: one reusable 2-state cycle, optional People, range-time forecasting, sparse one-day overrides and responsive desktop/mobile setup and editing. The requested 2/2/3/2/2/3 shared-care pattern is pre-filled without hardcoding household names or generating daily events. |
| 2026-08-09 | Shipped the v0.19.3 interaction/UI follow-up: Homestead maintenance can create or update its single Solace cost, Calendar source events link back to their owning node, linked finance badges open filtered cross-node views, touch-only controls remain visible on coarse pointers, and dense Solace/Education desktop layouts use wider screens. No new architectural decision. |
| 2026-08-09 | Added **D22**, Roadmap Milestone 5.5 and node spec `26_Node_Home_Assistant.md`: Home Assistant is an important dedicated bridge with REST-first read-only status, safe allowlisted controls, approved HomeStack events, explicit security/availability gates and no duplicated state/domain ownership. |
| 2026-08-04 | Shipped the focused phone usability and Hub follow-up (v0.19.1): compact section pickers for Solace/Homestead/Education, collapsed Solace creation forms, corrected Solace card spacing, visible touch actions, stacked Homestead maintenance controls, actionable node search results, background-scroll locking for the mobile More sheet, and a configurable household countdown widget. No new architectural decision. |
| 2026-08-04 | Shipped the household-launch mobile experience (v0.19.0): partner-friendly phone navigation/defaults, mobile Hub shortcuts, profile editing, improved shared spacing/tabs/modals/sign-in, readable mobile Calendar month and Solace schedule views, actionable notifications, richer quick-create choices, and an admin setting to disable Solace's extra password-on-entry gate without removing role permissions or auditing. No new architectural decision. |
| 2026-08-04 | Shipped Homestead room and area planning (v0.18.0): stable linked room pages, unified purchase/maintenance/renovation/upgrade items, active/completed/archived lifecycle, estimated and actual costs, exact room/household summaries, future floor-plan metadata, and permission-aware local/global search. No new architectural decision. |
| 2026-08-04 | Started the remaining M4 security-maturation work (v0.17.0): protected shared attachments, central record visibility/sensitivity enforcement, audited sensitive downloads, removal of public media serving, visibility-checked Education file downloads and five-minute expiring password re-authentication. No new architectural decision. |
| 2026-07-30 | Shipped Solace bills-account forecasting and deep workflow parity (v0.16.0): dated 3–24 month cash flow and safe-withdrawal calculation, bill stop/autopay/history/edit-scope controls, current/next pay plans and checklists, complete payday steps, purchase quick-saving, calculated upcoming income dates, normalised category reports and expanded health checks. No new architectural decision. |
| 2026-07-29 | Completed standalone Project Solace feature parity (v0.15.0): closeout/reconciliation, account-balance projections, finance health, custom categories, complete record management, checklist preferences, settings/cycle anchors, required set-aside and shortfall reporting, consolidated workspace loading, CSV/XLSX export and reviewed import, generic finance-safe reminders, and full-state standalone migration validated against the live local database. No new architectural decision. |
| 2026-07-29 | Shipped Solace recurring bill parity (v0.14.0): independent paid/skipped occurrences, month-end-safe recurrence generation, monthly bill/income calendar and list, complete bill management/cost summaries, legacy occurrence import and working finance Hub renderers. No new architectural decision. |
| 2026-07-29 | Shipped native Solace pay-cycle planning (v0.13.0): structured bucket allocation rules, per-income/household transfer calculations, pausable income sources and idempotent cycle-checklist generation. No new architectural decision. |
| 2026-07-29 | Shipped the daily-use experience milestone (v0.12.0): permission-aware global search, universal quick-create, URL-backed navigation state, custom mobile navigation, route splitting/caching, session-expiry reliability, responsive/accessibility consistency and API response timing. No new architectural decision. |
| 2026-07-28 | Updated **D21**: Homestead now owns protected home insurance/account context and mirrors active costs to linked Solace bills through events (v0.11.2). |
| 2026-07-21 | Added **D21** (Homestead is the home/property hub; folds the *home* scope of the planned Assets node). Added node spec `25_Node_Homestead.md`. Shipped the Homestead node end-to-end (v0.10.0). |
| 2026-06-25 | Added **D19** (Meridian = full functional port of the standalone app) and **D20** (achievements/badges as a shared cross-node system). Rewrote `15_Node_Meridian.md` and `MILESTONE_2_Checklist.md` to the full-port scope after an audit found only a thin subset had been built. |
| 2026-06-23 | Consolidated all prior docs into this set. Baked in decisions D1–D18. Dropped multi-household behaviour (kept tenant column). Switched to session auth, signal-based decoupling, Postgres FTS. Reordered roadmap for solo dev. Set Meridian/Solace to native rebuild-shell/reuse-logic/migrate-data, no iframe layer. |
| *(earlier)* | Prior "Doc 00" update pack revised originals around the confirmed node model. Now superseded. |
