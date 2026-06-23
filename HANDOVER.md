# HANDOVER.md — HomeStack

> **Read this first if you are a coding assistant.** It tells you what HomeStack is, the rules
> you must not break, what is done, and what to do next. Then read the canonical docs (below)
> before writing code. At the **end of every working session, append to the Progress Log** so
> the next assistant can continue cleanly.

---

## 1. What HomeStack is

A secure, modular, **self-hosted** household management platform for **one household** (two
adults, two children), run on an always-on home server via Docker Compose. It replaces scattered
apps with one warm, family-oriented system: a **Hub** ("what needs attention today?"), a
**Calendar** (the household timeline), opt-in **nodes** (areas of household life), and a
touchscreen **kiosk** the kids use.

Built solo. May *one day* be released as a **self-hosted** product other families run themselves
(never SaaS). That ambition only disciplines which decisions are permanent — it does not expand
current scope.

## 2. Canonical documentation (source of truth)

Read these in `docs/`. **If anything conflicts, this doc set wins.** Older `.docx` files are
archived/superseded — ignore them.

- `00_README_and_Changelog.md` — **all key decisions (D1–D18) with reasoning. Read this.**
- `01_Master_Software_Specification.md` — vision, node model, V1 scope.
- `02_Software_Architecture_Document.md` — architecture, base model, resolver, helpers.
- `03_Database_Design_Document.md` — schema and conventions.
- `04_Development_Roadmap.md` — milestones with "done when".
- `05_Security_Architecture_Document.md` — auth, permissions, sensitive nodes, kiosk.
- `06_API_Specification.md` — endpoints.
- `07_UIUX_Design_Guide.md` — design system, kiosk/child UX.
- `08_Coding_Standards_and_Project_Structure.md` — **how to write the code. Read this.**
- `09_Node_Model_Decision_Record.md` — why these nodes.
- `10_Future_Features_Parking_Lot.md` — what is deferred vs out of scope.
- `11`–`22_Node_*.md` — per-node specs (Atlas, Home Wiki, Pets, Education, Meridian,
  Inventory, Assets, Hearth, Travel, Projects, Health, Solace).
- `MILESTONE_1_Checklist.md` — the current build checklist (tick boxes as you go).

## 3. Hard rules (do NOT violate these)

These are settled decisions. If you think one is wrong, **flag it in the Progress Log and ask —
do not silently override it.**

1. **Single household, keep the tenant column (D1).** Every user-facing model inherits
   `HouseholdBaseModel` (household FK + soft delete + created/updated-by-user). Don't build
   multi-household signup/billing/isolation. Don't drop `household_id`.
2. **No SaaS / multi-household behaviour (D2).** Productization, if ever, is self-hosted.
3. **API-first (D3).** All clients talk to `/api/v1/`. Business logic in the backend.
4. **No durable event bus (D4).** Node decoupling uses Django signals behind the thin
   `apps/events/` interface. **No `event_bus_events` table, no broker.** Nodes never import each
   other's models.
5. **No Celery/Redis yet (D5).** Scheduled work runs via a Django management command on cron.
   Add Redis/Celery only when a feature genuinely needs background processing.
6. **Session auth, avatar + PIN (D6).** No token auth until native apps exist. Sensitive re-auth
   uses a **password**, not the PIN. PIN + password hashed with **Argon2id**.
7. **Calendar has one source of truth (D7).** Node records own their dates. The `scheduling`
   helper creates/updates/deletes `calendar_events` and writes `calendar_event_id` back. **Nodes
   never write calendar rows directly.**
8. **One recurrence format (D8):** `recurrence_rule` (RRULE) on the owning record. No parallel
   `repeat_rule`.
9. **Search via Postgres FTS (D9)** in selectors. No hand-maintained `search_index` table.
10. **Central permission resolution (D10).** One resolver + one visibility queryset mixin. **No
    ad-hoc permission checks in views. Permission tests are written FIRST.**
11. **Attachments: `visibility` + `sensitivity` only (D11).** No per-row ACL table in V1.
12. **People vs. Users (D12):** `created_by`/`updated_by`/ownership/audit = **user**;
    `assigned_to`/subject = **person**. People may have no login.
13. **Meridian early, Solace after security (D13).** Both are **native nodes**, not external
    integrations. **No iframe / external-link layer. No `integrations` app.**
14. **Migrate Meridian/Solace by rebuild-shell + reuse-logic + import-data (D14).** Rebuild
    models/serializers/views on shared services; reuse their proven business logic; one-time
    dry-runnable import script in `scripts/`.
15. **No household specifics in schema or logic (D15).** No "two cats", no hardcoded names. Keep
    everything general for a future buyer.
16. **Calendar app is named `scheduling` (D16)**, not `calendar` (avoids stdlib clash).
17. **Backups define a working restore (D17).** Restore is tested, documented, admin-re-auth
    gated.
18. **Walking skeleton first (D18).** Build the Milestone 1 vertical slice before any other node.

### Per-app layering (Coding Standards §6)
Views are **thin** → delegate to `services` (writes) and `selectors` (reads). Every app:
`models, serializers, views, urls, permissions, services, selectors, events, tasks, tests`.

## 4. Tech stack

Backend: Python · Django · DRF · PostgreSQL. Frontend: React · TypeScript · Vite · TailwindCSS.
Deploy: Docker Compose on a Linux home server, local-network only (HTTPS/reverse-proxy/VPN
before any remote access). Redis/Celery and the mobile/desktop tech choice are deferred.

## 5. Current status

**Phase: planning complete; code not started.**

- [x] Documentation consolidated to one canonical set (docs 00–22 + Milestone 1 checklist).
- [x] All architectural decisions made (D1–D18).
- [ ] **Milestone 1 (Walking Skeleton) — NOT STARTED.** ← *this is the active task.*
- [ ] Milestone 2: native Meridian.
- [ ] Milestone 3: Home Wiki, Pets, Education.
- [ ] Milestone 4: security maturation.
- [ ] Milestone 5: native Solace.
- [ ] Milestone 6: Inventory, Assets, Hearth, Travel, Projects, Health.

## 6. Active task — Milestone 1

Build the vertical slice in `MILESTONE_1_Checklist.md`, in order:
Docker scaffold → Django + settings → Household + base model → Accounts/auth → People →
**Permissions (tests first)** → Settings/audit → Scheduling + helper → Atlas → Hub → Kiosk shell
→ Backups + restore → Frontend slice.

**Definition of done:** family logs in (web + kiosk), uses Atlas lists/reminders, sees them on
Hub and Calendar, permissions enforced and tested, backup **and restore** work, runs in Docker,
used daily.

**Suggested next concrete step if nothing exists yet:** Phase 1.0 — scaffold the repo and a
3-service `docker-compose.yml` (backend, frontend, postgres), confirm it boots.

## 7. Guardrails — common ways to get this wrong

- Don't add Redis/Celery/event-bus tables "to be safe" — they're deliberately deferred.
- Don't put permission checks in views — use the resolver/mixin.
- Don't let a node write a `calendar_event` directly — call the scheduling helper.
- Don't import one node app's models into another — communicate via signals.
- Don't add a second auth system for Meridian/Solace — they use shared Users/People.
- Don't hardcode anything specific to this household.
- Don't skip permission tests — they come first.

## 8. Open questions / decisions still pending

*(Append here when something needs the owner's call. None blocking Milestone 1 currently.)*

- Mobile/desktop client tech (React Native vs. Tauri vs. PWA) — deferred until after core
  product proves itself (D3). PWA is the likely first bridge.

## 9. Progress Log

> **Append a dated entry at the end of every session.** Newest at the bottom. Keep it factual:
> what you built, what you changed, what's half-done, what the next assistant should pick up.

| Date | Author (assistant/human) | Milestone | What changed | Next step |
|------|--------------------------|-----------|--------------|-----------|
| 2026-06-23 | Planning | M0 | Consolidated docs 00–22, Milestone 1 checklist, this handover. No code yet. | Start Phase 1.0 (Docker scaffold). |

### Session notes (free-form, optional)

*(Use this space for anything that doesn't fit the table — gotchas, decisions made mid-session,
things you were unsure about. Date each note.)*

---

## 10. How to update this file

At the **end of your session**: (1) tick the boxes you completed in `MILESTONE_1_Checklist.md`;
(2) update **§5 Current status** if a milestone's state changed; (3) add a **Progress Log** row;
(4) if you made or hit a decision, note it in **§8**; (5) if you had to deviate from a Hard Rule,
say so explicitly in the log and explain why. Keep this file honest — it is the memory that lets
the next assistant continue without re-reading everything.
