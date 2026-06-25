# HomeStack Documentation — README & Changelog

**Status:** Canonical source of truth. This consolidated set supersedes all earlier
`.docx` files in the project, including the previous Doc 00 update pack and the original
standalone documents. Archive the old files; do not edit them further.

**Last revised:** 2026-06-25
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
| *(to follow)* | Security, API, UI/UX, Coding Standards, Parking Lot, Node specs. |

The node specifications (Atlas, Home Wiki, Pets, Education, Inventory, Assets, Hearth,
Travel, Projects, Health, Meridian, Solace) remain largely valid from the previous pack
and will be folded in next; where they conflict with anything here, **this set wins**.

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

---

## Change history

| Date | Change |
|------|--------|
| 2026-06-25 | Added **D19** (Meridian = full functional port of the standalone app) and **D20** (achievements/badges as a shared cross-node system). Rewrote `15_Node_Meridian.md` and `MILESTONE_2_Checklist.md` to the full-port scope after an audit found only a thin subset had been built. |
| 2026-06-23 | Consolidated all prior docs into this set. Baked in decisions D1–D18. Dropped multi-household behaviour (kept tenant column). Switched to session auth, signal-based decoupling, Postgres FTS. Reordered roadmap for solo dev. Set Meridian/Solace to native rebuild-shell/reuse-logic/migrate-data, no iframe layer. |
| *(earlier)* | Prior "Doc 00" update pack revised originals around the confirmed node model. Now superseded. |
