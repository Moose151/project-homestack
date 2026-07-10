# Document 7 — Development Roadmap

> Canonical. Supersedes all earlier roadmap versions. Tuned for a solo developer building for
> one household on an always-on home server. Decisions D1–D18 in `00_README_and_Changelog.md`.

## Guiding principle

Build **vertically, not horizontally**. The biggest risk for a solo project this broad is
spreading a little effort across every node and never finishing one usable path. So the first
milestone is a complete, daily-usable vertical slice; every milestone after it adds one node
end-to-end. The "sell it later" ambition disciplines which decisions are permanent — it does
not add scope.

Each milestone has an explicit **Done when** so you can tell when to move on.

---

## Milestone 0 — Planning (complete)

This documentation set, the node-model decision, and the architectural decisions (D1–D18).

**Done when:** docs are consolidated to one source of truth (this set) and the old `.docx`
files are archived.

---

## Milestone 1 — Foundation / Walking skeleton (D18)

The single most important milestone. A thin but complete vertical slice you actually use.

Build:
- Docker Compose: `backend` (Django/DRF), `frontend` (React/TS/Vite/Tailwind), `postgres`.
  *(No Redis/Celery yet — D5.)*
- `HouseholdBaseModel` + household-scoped default manager + soft delete (D1).
- Seed the single household row.
- Session-based auth: avatar + PIN, plus admin/manager passwords (Argon2id) (D6).
- Users + People, with the user/person rule wired in (D12).
- The **central permission resolver + visibility queryset mixin**, with permission tests
  written first (D10).
- Settings shell and audit logging.
- **Backups with a working, documented restore** (D17).
- **Atlas** as the one real node (notes, lists, list items, simple reminders).
- **Hub + Calendar** (`scheduling`) with the shared event-generation helper (D7), so Atlas
  reminders appear on the calendar without double-writing dates.
- Kiosk shell: ambient → avatar → PIN → dashboard → timeout.

**Done when:** the family can log in (web and kiosk), use Atlas lists/reminders, see them on
the Hub and Calendar, permissions are enforced and tested, and you can back up and *restore*
the database. You use it daily.

---

## Milestone 2 — Native Meridian (D13, D14)

The highest-joy early win: it's already built, already used, kid-facing, and the heart of the
kiosk. No sensitive data, so it doesn't need the security maturation first.

Build:
- Native Meridian node on shared Users/People, scheduling, permissions, Hub widgets, kiosk UI.
- Reuse the proven reward/points/approval logic; rebuild only the shell.
- One-time import of the household's live Meridian data.

**Done when:** Meridian runs entirely inside HomeStack — tasks, points, rewards, approvals,
kid kiosk cards and celebrations — and the standalone Meridian app is no longer needed at home.

### Milestone 2 revisit — Meridian parity and adult cockpit (owner request, 2026-07-10)

After live use, the Meridian integration was judged too thin/clunky despite the earlier full-port
checkoff. Product direction: **HomeStack is the Meridian source of truth and the adult/admin
cockpit** (approvals, task/reward setup, monitoring, reports, settings), while the native
Meridian app at `/home/instructor/Documents/new/project-meridian` remains the behaviour/style
reference and may remain/adapt as the child-facing client.

Build:
- Behaviour parity first, starting with native-style task completion history: per-person
  submissions, shared/household completion rules, recurring-cycle re-arm, evidence placeholder,
  review notes, approval/rejection history, and admin complete-for-person.
- Adult cockpit UI in HomeStack: overview approvals queue, task/reward management, stock and
  setup, monitoring, points/reports, and settings. Keep it HomeStack-consistent rather than a
  jarring clone of the child-facing native app.
- Defer deeper kid-facing delight work until the source-of-truth/adult workflows are solid.

**Done when:** an adult can manage day-to-day Meridian from HomeStack without needing the legacy
admin screens: approve/reject submissions and purchases, create/edit/archive tasks and rewards,
monitor balances/activity/history, and trust the completion/ledger behaviour to match native
Meridian rules.

---

## Milestone 2.5 — Core surfaces: Hub, Atlas, Calendar (owner request, 2026-06-25)

Inserted before M3 at the owner's request. With Meridian done, the daily-use core surfaces —
the **Hub**, **Atlas**, and the **Calendar** — need to actually function and feel good before
we add more nodes on top of them. These are the screens the family touches most; getting them
right makes every later node land better. Specs: `23_Core_Hub.md`, `11_Node_Atlas.md`,
`24_Core_Calendar.md`.

Build, three workstreams:

**A. Hub — functionality & usability.**
- Per-household widget config (enable/disable, order, size) and per-user overrides (hide/
  reorder), with endpoints (the config API is currently unbuilt) and a clean web UI.
- **Establish the "every node ships its Hub widget" pattern** — a node is not done until it
  contributes its Hub widget(s) via a seeded `HubWidget` row + a permission-filtered selector
  (no cross-imports, D4). Backfill the **Meridian Hub widget** (today's tasks / points summary,
  kiosk-safe) now, and add this requirement to every node's completion criteria going forward.
- Wire the Calendar "upcoming events" widget once Calendar views land (workstream C).
- Keep it permission- and kiosk-filtered; calm, glanceable defaults. (Ambient widgets —
  clock/photo/greeting — optional low-effort nicety; **weather** stays parked, D5.)

**B. Atlas — improve functionality & usability.**
- Gap pass against `11_Node_Atlas.md`: tighten lists/items/checklists/reminders UX on web and
  kiosk, quick-add/quick-capture, grocery/shopping mode polish, due-dates and person assignment,
  clearer visual states.
- Replace the SQLite-safe `icontains` search with Postgres FTS (D9) in Atlas selectors.
- Make dated Atlas items render properly on the new Calendar (they already sync via the helper).

**C. Calendar — build the core.**
- Build the real Calendar UI beyond today's "upcoming list": month / week / day / agenda views,
  per-person colour coding, and filters (by node/source, person, visibility).
- **Accessible from every page** (persistent entry point + a lightweight peek/mini-calendar +
  quick-add), **easily configurable** (saved default view, filters, start-of-week/time-format
  as prefs), and **nice to look at** (shared design system, dark-mode, kiosk-safe view).
- Standalone event CRUD UI; node-derived events continue to flow only through the scheduling
  helper (D7). RRULE expansion may be tackled here or deferred per `24_Core_Calendar.md` (D8).

**Done when:** the Hub shows the right per-user "today" items including a live Meridian widget and
is configurable; Atlas is pleasant and capable for daily list/reminder use on web and kiosk with
FTS search; the Calendar offers month/week/day/agenda views, is reachable from every page, is
configurable, looks good, and shows all permitted node + standalone events with no double-writing.
Permissions enforced throughout; all three follow the shared design system; used daily.

---

## Milestone 3 — Home Wiki, Pets, Education

Round out everyday household value.

Build, one node at a time, each fully end-to-end (models → API → permissions → search via
Postgres FTS → calendar via the helper → Hub widgets → kiosk view where relevant → tests):
- **Home Wiki** — pages, categories, favourites, emergency info, kiosk-safe read view.
- **Pets** — profiles, treatment/vaccination reminders, vet appointments.
- **Education** — institutions, courses, assessments/homework, school events; kiosk homework
  cards.

**Done when:** each node delivers real daily value and the family reaches for HomeStack over
the old separate tools.

---

## Milestone 4 — Security maturation

Harden the sensitive-data machinery before any finance or health data goes in.

Build:
- Sensitive-node re-authentication (password-based, defined for web and kiosk) (D6).
- Audit coverage for sensitive access, permission changes, backups, sensitive downloads.
- Sensitive-node locking and the sensitivity dimension fully enforced through the resolver.
- Attachment permission checks (`visibility`/`sensitivity`) hardened (D11).
- Pre-remote-access checklist satisfied if you ever want VPN access (HTTPS, reverse proxy,
  rate limiting, strong admin passwords).

**Done when:** a sensitive node can be locked, re-auth works on web and kiosk, and access is
audited.

---

## Milestone 5 — Native Solace (D13, D14)

Now that sensitive machinery exists, migrate finance in natively.

Build:
- Native Solace node on shared services; `sensitivity = financial`; re-auth required; hidden
  from children/users by default; access audited.
- Reuse the proven bill-recurrence and payday-checklist logic; rebuild the shell.
- One-time import of the household's live Solace data.

**Done when:** only authorised users reach Solace, finance never leaks into unauthorised Hub/
Calendar/Search/kiosk views, and the standalone Solace app is no longer needed at home.

---

## Milestone 6 — Remaining nodes (as appetite allows)

Each built end-to-end, one at a time, in roughly this order:
**Inventory → Assets → Hearth → Travel → Projects → Health.**

- Inventory and Assets pair naturally (consumables vs. owned items).
- Hearth benefits from Inventory existing (pantry checks, grocery generation via Atlas).
- **Health is last** and only after security maturation is proven (it already is, post-M4);
  all Health data sensitive by default.

**Done when:** each node meets its completion criteria in its node spec.

---

## Milestone 7 — Infrastructure as needed

Add only when a feature demands it (D5):
- Redis + Celery + Celery-beat once reminders/background work outgrow the cron management
  command.
- Push/email notification channels.

**Done when:** background-dependent features work reliably; not before.

---

## Milestone 8 — Productization (only if it's genuinely good)

Pursue only after HomeStack has fully replaced Meridian and Solace for your household and is
used daily — that daily use is the proof it's worth releasing.

Consider:
- A clean install/onboarding flow and self-host setup docs.
- First-run wizard (create household, admin, enable nodes).
- A PWA as the first phone bridge (D3), before committing to native app tech.
- Licensing decision and a public repo/release.
- Confirm the **self-hosted** model (D2) — no SaaS, no custody of others' data.

**Done when:** another household could install and run HomeStack from your docs without you.

---

## What is explicitly NOT on this roadmap for now

Native mobile/desktop apps, full offline mode, OCR/AI, plugin system, public internet
exposure, external calendar sync, field-level encryption, and any multi-household/SaaS
behaviour. These stay in the Parking Lot until the core product earns them.
