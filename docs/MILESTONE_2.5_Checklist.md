# Milestone 2.5 — Core surfaces (Hub · Atlas · Calendar): Build Checklist

> Canonical for M2.5. Global rules from `00_README_and_Changelog.md` (D1–D20) apply. Inserted
> before M3 at the owner's request (2026-06-25): with Meridian done, the daily-use core surfaces
> need to actually function and feel good before more nodes land on top of them.
>
> Specs: `23_Core_Hub.md` (Hub), `11_Node_Atlas.md` (Atlas), `24_Core_Calendar.md` (Calendar).
> Built on the proven layered pattern (models → services → selectors → serializers → thin views →
> urls → permissions → calendar/events helpers → web UI → kiosk UI → tests).
>
> Checkbox legend: `[ ]` todo · `[~]` partial/needs work · `[x]` done.
>
> **Starting state (2026-06-25):** Hub has the three config models (`HubWidget`/`HouseholdHubWidget`/
> `UserHubWidget`) + `GET /hub/` + `GET /hub/kiosk/`. Widgets seeded: `atlas_todos`/`atlas_reminders`
> **and the five Meridian widgets** (migration `0003`, content logic in `hub/services.py`); the
> **kiosk** already renders Meridian widgets via a `WIDGET_COMPONENTS` registry. The **web** Hub
> previously rendered only the two Atlas widgets (everything else fell through to the reminders
> renderer) — **fixed 2026-06-25** (web now renders Meridian tasks/points/reward-requests; see
> Phase 2.5A.3). Still **no widget-config endpoints** (enable/order/size / per-user reorder).
> Atlas has full CRUD + web/kiosk UI but searches via SQLite-safe `icontains`. Calendar has
> `CalendarEvent` + CRUD API + a web "upcoming events" list — **no month/week/day/agenda views,
> not reachable from every page**.

---

## Workstream A — Hub: functionality & usability

## Phase 2.5A.1 — Widget config API ✅ (2026-06-25)
- [x] `GET /api/v1/hub/widgets/` — catalogue + household enable/order/size + per-user state
      (`hub/selectors.list_widget_config` + `HubWidgetConfigSerializer`).
- [x] `PATCH /hub/widgets/<key>/` — household config (enable/disable, `display_order`, `size`);
      gated `hub.edit` (new perms migration `0013`; admin/manager).
- [x] `PATCH /hub/widgets/<key>/me/` — per-user hide/show + reorder (`permission_action = "view"`,
      applies to self only).
- [x] `get_hub_widgets` now scopes to `user.household` and applies per-user **reorder** (user order
      wins) + hide. Tests: config list, admin-configures, non-admin 403, user-hides-own, bad key 400
      (**20 hub tests green**).

## Phase 2.5A.2 — Hub configuration UI (web) ✅ (2026-06-25)
- [x] `HubConfig` panel toggled from the Hub header ("⚙ Customise"). "Your Hub" section: show/hide
      + up/down reorder (per-user). "Household defaults" section (admin only): enable/disable + size.
- [x] Permission-aware (household controls only render for admins); each change re-fetches and
      refreshes the live Hub. *(Drag-and-drop deferred; up/down reorder shipped.)*

## Phase 2.5A.3 — Per-node Hub-widget pattern + Meridian widget
- [x] **Establish the rule:** a node is not "done" until it ships its Hub widget(s) — a seeded
      `HubWidget` row (`source_node` set, `supports_kiosk` as appropriate) + a permission-filtered
      selector the Hub service calls. **No cross-imports** (D4). Add this to every node's completion
      criteria going forward (and to the M3 node specs' Hub-integration sections). Added to Home
      Wiki, Pets and Education specs.
- [x] **Build the Meridian Hub widget(s):** seeded (migration `0003`: my_tasks, hot_tasks, points,
      pending_approvals, reward_requests) + content via `hub/services._meridian_widget_content`
      reading Meridian **selectors** (no model cross-import).
- [x] Verify Atlas + Meridian widgets render real data **end-to-end**: kiosk already had a widget
      registry; **web HubPage now renders Meridian tasks/points/reward-requests** (2026-06-25,
      `tsc` + build clean). *Live home-server smoke-test still worth doing.*
- [x] Refactor note: `hub/services.py` still dispatches widget content by `if key == …`. A
      widget-provider registry is explicitly **parked** until a third node contributes widgets;
      the current Atlas/Meridian/Calendar dispatch is covered by tests and kept intentionally
      small.

## Phase 2.5A.4 — Usability polish 🟡 (2026-06-25 — Calendar widget pending C)
- [x] Size-aware responsive grid (small = 1 col, medium/large = full width on `sm+`); clearer
      empty-state pointing at Customise; dark-mode aware (shared tokens).
- [x] Ambient **clock** widget (`source_node = null`, kiosk-safe, seeded enabled via hub migration
      `0004`) — rendered client-side on web (`ClockWidget`) and kiosk (registry). Demonstrates the
      ambient/non-node widget path. **Weather stays parked** (external fetch + caching, D5).
- [x] Calendar "upcoming events" widget wired once Workstream C landed — see Phase 2.5C.6.

---

## Workstream B — Atlas: improve functionality & usability

## Phase 2.5B.1 — Search → Postgres FTS (D9) ✅ (2026-06-25)
- [x] `atlas/selectors._search` helper: Postgres `SearchVector`/`SearchQuery` when
      `connection.vendor == "postgresql"`, else `icontains` fallback (SQLite tests). Applied to
      `search_notes` + `search_atlas` over note title/body, list title, list-item title/notes,
      reminder title/body. *(Tags/categories not modelled in Atlas V1 — parked.)*
- [x] **Fixed a visibility leak:** `search_atlas` now permission-filters lists + reminders, and
      restricts item hits to lists the user may see. New unified `GET /atlas/search/?q=`.
- [x] Tests: search spans notes/lists/items/reminders; child never sees a sensitive note; items
      from a private list don't surface to a child; blank query returns empty (**47 atlas tests**).

## Phase 2.5B.2 — Functionality gap pass (vs `11_Node_Atlas.md`) 🟡 (2026-06-25)
- [x] Items gained `due_at` + `quantity` (migration `0002`); `assigned_to_person` + `position`
      already existed. Serializers expose them + `atlas_list_id`; services allow-list updated.
- [x] Grocery/shopping mode: per-item `quantity` (web shows a Qty input on grocery/shopping lists,
      renders `2× Milk`). *(Category sort parked — items have no category field; templates parked.)*
- [x] Quick-add lives on the Hub (Atlas widgets) + the Atlas page; richer cross-surface quick
      capture is **parked** for mobile/PWA. Item-level calendar sync stays out by decision (only
      reminders sync, D7).

## Phase 2.5B.3 — Atlas UX (web + kiosk) 🟡 (2026-06-25)
- [x] Web Atlas: page-level **error banner** (mutations no longer swallow failures), due-date
      badges on items, quantity prefix, plus an **Atlas-wide search box** (debounced → `/atlas/search/`,
      grouped results).
- [x] Dated reminders already sync to the calendar via the helper (D7) — verified unchanged.
- [x] Kiosk Atlas: large list cards / shopping ticking deferred — **by design**, children cannot
      complete items (resolver blocks child non-view actions, D10); the kiosk Atlas widgets stay
      read-only. Adult-facing kiosk browse/ticking is parked until requested.

---

## Workstream C — Calendar: build the core

## Phase 2.5C.1 — List/query API hardening ✅ (2026-06-25)
- [x] `GET /calendar/events/` accepts `start`/`end` window + `node` (source key) + `person`
      filters (`_parse_dt` handles ISO datetime or date); all permission-filtered (D10). Serializer
      now exposes `source_node` (key) for display/filter/colour.
- [x] Synced events stay read-only via the API (existing 400 guard, D7); standalone CRUD intact.
      Tests: window, person filter, source_node key (**23 scheduling tests**).

## Phase 2.5C.2 — Calendar views (web) ✅ (2026-06-25)
- [x] Month grid + week (7-day columns) + day (timed list) + agenda views, prev/today/next nav,
      period label. Per-person colour coding (`colour` → person colour → node colour → default) with
      an always-visible people **legend**. Today marker, calm empty-states, dark-mode tokens.

## Phase 2.5C.3 — Accessible from every page (owner requirement) ✅ (2026-06-25)
- [x] `CalendarPeek` popover in the global shell header (every authenticated page): next 5 events +
      **quick-add** + "Open calendar". Persistent Calendar nav entry already existed.
- [x] Deep-links from dated Atlas reminders and Hub upcoming/calendar widgets → Calendar day view
      (`/calendar?date=YYYY-MM-DD`) added; Calendar opens directly in day view for the linked date.

## Phase 2.5C.4 — Configurable (owner requirement) 🟡 (2026-06-25)
- [x] Saved **default view** + **start-of-week** + **12/24h** persisted per device (localStorage);
      filter layers by **source/node** and **person** (visibility already enforced server-side, D10).
- [x] Household-level defaults an admin can set — **parked for post-M2.5**. Per-device localStorage
      covers V1 without introducing a preferences store.

## Phase 2.5C.5 — Standalone events + recurrence ✅ (2026-06-25)
- [x] Event modal: create/edit/delete standalone events (title, start/end, all-day, person, colour,
      location, visibility). Synced events open read-only with an "edit in <node>" note (D7).
- [x] RRULE: **deferred** per `24_Core_Calendar.md` (D8) — events store/display the rule; no
      occurrence expansion engine yet (recurring events render once at their start).

## Phase 2.5C.6 — Calendar Hub widget (closes A.4 leftover) ✅ (2026-06-25)
- [x] `calendar_upcoming` widget seeded (hub migration `0005`, `source_node=null`, kiosk-safe),
      content from scheduling selectors; rendered on web Hub (`UpcomingWidget`) + kiosk registry.

---

## Workstream D — UI/UX fixes (owner, 2026-06-25)

A batch of usability fixes raised by the owner. Small but high-touch; do alongside A–C.

## Phase 2.5D.1 — Kiosk enter/exit button ✅ (2026-06-25)
- [x] "Enter kiosk" affordance in the web shell sidebar (`<a href="/kiosk">`, full nav into the
      separate kiosk route tree).
- [x] "Exit kiosk" affordance on the kiosk ambient screen (corner link → `/`, stops propagation
      so it doesn't trigger "tap to start").
- [x] "Web mode" affordance on the kiosk dashboard header (link → `/`) so an authenticated kiosk
      user can return to the normal web UI.

## Phase 2.5D.2 — Hide estimated cost from non-admins (shop + wishlist) ✅ (2026-06-25)
- [x] `price_estimate` visible to **admins only** — `AdminOnlyPriceMixin` on the reward, wishlist-
      item and group-goal serializers pops the field unless `request.user.role == "admin"` (fails
      closed if no request in context). Threaded `context={"request": request}` through all Meridian
      output call sites (input `data=request.data` sites untouched).
- [x] Backend tests: non-admin reward-list omits `price_estimate`; admin keeps it. **74 meridian
      tests green.**

## Phase 2.5D.3 — Type PINs with the physical keyboard ✅ (2026-06-25)
- [x] Web `PINPad` and kiosk `PINEntry` accept digits + Backspace from a hardware keyboard via a
      `window` keydown listener (kiosk also maps Esc → cancel). On-screen pad still works.

## Phase 2.5D.4 — User tiles for web login (replace username field) ✅ (2026-06-25)
- [x] Web `LoginPage` now shows selectable user **avatar tiles** (from `getKioskUsers`) → PIN.
      Kept a **"Sign in with a username instead"** fallback so no one is locked out if a user has
      no linked Person. *(Decision resolved: `seed_admin` + `create_user` both link a Person, so
      all login users appear; the manual fallback covers edge cases.)*

## Phase 2.5D.5 — Emoji account pictures (like Meridian/Solace) ✅ (2026-06-25)
- [x] Emoji account pictures stored in `User.avatar` (CharField). `Avatar` now renders
      **emoji → image → initials** (`isImageAvatar` helper distinguishes a URL/path from an emoji).
      Emoji **picker** (preset grid + clear) on the admin Users create/edit forms; avatar shown in
      the user-list rows. `kiosk-users` now returns the **account** avatar (`User.avatar`, falling
      back to `Person.avatar`) so emoji appear on the web login tiles, kiosk avatar-select and PIN
      screens. **352 backend tests green; `tsc` + build clean.**

## Phase 2.5D.6 — Kiosk look & feel + light/dark toggle
- [x] Restyled the kiosk toward the **original Meridian kiosk** using the legacy reference found at
      `/home/moose/Documents/project-meridian` (the handover path `~/Documents/new/project-meridian`
      did not exist): warm HomeStack surfaces, raised cards, primary/warning/success accents, and no
      hardcoded `bg-gray-*`/`text-gray-*` kiosk styling.
- [x] Light/dark mode toggle on the kiosk (ambient, avatar select, PIN, dashboard) using the shared
      `hs-dark` preference and semantic design tokens.

---

## Cross-cutting

## Phase 2.5X — Verify & wire together
- [x] Atlas reminders → appear on Hub widget **and** Calendar with no double-writing (D7). Covered
      by `HubContentTests.test_dated_reminder_appears_on_hub_and_calendar_once`.
- [x] Meridian Hub widget + Calendar Meridian deadlines render for the right roles only. Covered by
      scheduling visibility tests for private Meridian deadlines and existing Hub widget tests.
- [x] Permissions enforced across all three surfaces (no leaks to children/guests); tests added.
      Added Hub todo visibility regression for private Atlas lists plus Calendar source visibility
      tests.
- [x] Kiosk light-theme contrast pass: current light kiosk UI feels too washed/flushed; improve
      contrast between the background and widgets/tiles while staying on shared design tokens.
- [x] Add a kiosk Calendar view/surface (beyond the existing `calendar_upcoming` Hub widget) so the
      household timeline is directly usable from kiosk mode, including month/week/day/agenda modes.
- [x] `tsc` + production build clean; backend suite green. Home-server run-through still happens as
      deployment operation after pull/rebuild/migrate.

---

## Definition of done (Milestone 2.5)

- [x] **Hub:** shows the right per-user "today" items; households configure (enable/order/size) and
      users hide/reorder; a live **Meridian Hub widget** renders (web + kiosk); the "every node
      ships its widget" pattern is documented and applied.
- [x] **Atlas:** pleasant and capable for daily list/reminder/checklist use on web and kiosk, with
      Postgres FTS search and dated items flowing to the Calendar.
- [x] **Calendar:** month/week/day/agenda views, reachable from every page (peek + quick-add),
      configurable, colour-coded, good-looking; shows all permitted node + standalone events with
      no double-writing.
- [x] Permissions enforced throughout; all three follow the shared design system. Home-server daily
      use/deploy remains an operational follow-through, not a code blocker.
</content>
