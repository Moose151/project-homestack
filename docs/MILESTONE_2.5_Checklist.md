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

## Phase 2.5A.1 — Widget config API
- [ ] `GET /api/v1/hub/widgets/` — catalogue + this household's enable/order/size state.
- [ ] Household config endpoint (admin/manager): enable/disable a widget, set `display_order`,
      set `size` (writes `HouseholdHubWidget`).
- [ ] Per-user override endpoint: hide/show + reorder for the current user (writes `UserHubWidget`).
- [ ] Resolution already layers catalogue → household → user → kiosk filter; add tests for the
      config write paths + permission gating (config = `hub.edit`; per-user = self only).

## Phase 2.5A.2 — Hub configuration UI (web)
- [ ] Settings surface to enable/disable, reorder (drag or up/down), and resize widgets.
- [ ] Per-user "my Hub" hide/reorder, distinct from household defaults.
- [ ] Permission- and kiosk-aware (children/guests never see config for widgets they can't view).

## Phase 2.5A.3 — Per-node Hub-widget pattern + Meridian widget
- [ ] **Establish the rule:** a node is not "done" until it ships its Hub widget(s) — a seeded
      `HubWidget` row (`source_node` set, `supports_kiosk` as appropriate) + a permission-filtered
      selector the Hub service calls. **No cross-imports** (D4). Add this to every node's completion
      criteria going forward (and to the M3 node specs' Hub-integration sections).
- [x] **Build the Meridian Hub widget(s):** seeded (migration `0003`: my_tasks, hot_tasks, points,
      pending_approvals, reward_requests) + content via `hub/services._meridian_widget_content`
      reading Meridian **selectors** (no model cross-import).
- [x] Verify Atlas + Meridian widgets render real data **end-to-end**: kiosk already had a widget
      registry; **web HubPage now renders Meridian tasks/points/reward-requests** (2026-06-25,
      `tsc` + build clean). *Live home-server smoke-test still worth doing.*
- [~] Refactor note: `hub/services.py` still dispatches widget content by `if key == …`. A
      widget-provider registry is the natural refactor once a third node contributes — deferred,
      consistent with the existing code comment.

## Phase 2.5A.4 — Usability polish
- [ ] Calm, glanceable defaults; clear empty-states; size-aware responsive grid; dark-mode.
- [ ] Wire the Calendar "upcoming events" widget once Workstream C lands.
- [ ] *(Optional, low-effort)* ambient clock / greeting widget (`source_node = null`). **Weather
      stays parked** — external fetch + caching, deferred per D5 (`23_Core_Hub.md` §6/§19).

---

## Workstream B — Atlas: improve functionality & usability

## Phase 2.5B.1 — Search → Postgres FTS (D9)
- [ ] Replace SQLite-safe `icontains` in Atlas selectors with Postgres FTS (`SearchVector`) over
      note title/body, list title, list-item text, tags, categories — permission-filtered.
- [ ] Children never see restricted notes in results; tests for the visibility filter.

## Phase 2.5B.2 — Functionality gap pass (vs `11_Node_Atlas.md`)
- [ ] Lists/items: due dates, `assigned_to_person`, display order, clearer completed states.
- [ ] Grocery/shopping mode: quantity, category sort, kiosk-friendly ticking, mobile shopping view.
- [ ] Checklists: reusable lists for repeated routines (templates/reset/duplicate stay parked).
- [ ] Quick-add / quick capture (note / list-item / reminder / to-do) from Hub + mobile + kiosk.

## Phase 2.5B.3 — Atlas UX (web + kiosk)
- [ ] Tighten the web Atlas pages (lists/reminders tabs) — clearer states, faster add/tick, error
      surfacing.
- [ ] Kiosk: large list cards, simple checklists, shopping-list ticking, minimal typing.
- [ ] Dated Atlas items render correctly on the new Calendar (they already sync via the helper, D7).

---

## Workstream C — Calendar: build the core

## Phase 2.5C.1 — List/query API hardening
- [ ] `GET /calendar/events/` date-window query (month/week/day ranges) + filters (source/node,
      `assigned_to_person`, visibility) — all permission-filtered through the resolver (D10).
- [ ] Synced (node-derived) events stay read-only via the API; standalone CRUD unaffected (D7).

## Phase 2.5C.2 — Calendar views (web)
- [ ] Month / week / day / agenda(list) views beyond today's "upcoming" list.
- [ ] Per-person colour coding (`assigned_to_person` + per-event `colour`); always-visible legend.
- [ ] Clear today marker; calm empty-states; dark-mode; shared design system ("nice to look at").

## Phase 2.5C.3 — Accessible from every page (owner requirement)
- [ ] Persistent Calendar entry point in the global shell on every authenticated page.
- [ ] Lightweight peek / mini-calendar (month strip or "next up" popover) openable from any page,
      with quick-add — no full navigation required.
- [ ] Deep-links: dated node items link straight to their day/event in the Calendar.

## Phase 2.5C.4 — Configurable (owner requirement)
- [ ] Saved default view; toggleable filter layers (by node/person/visibility).
- [ ] User prefs: start-of-week, time format, default view, default filters; household-level
      defaults an admin can set. Permission-aware (children never see sensitive layers).

## Phase 2.5C.5 — Standalone events + recurrence
- [ ] Standalone event create/edit/delete UI (title, start/end, all-day, person, colour, location,
      visibility/sensitivity).
- [ ] RRULE: decide expand-now vs defer per `24_Core_Calendar.md` (D8). If expanding, render a
      window of occurrences; otherwise display the rule and keep storage as-is.

---

## Workstream D — UI/UX fixes (owner, 2026-06-25)

A batch of usability fixes raised by the owner. Small but high-touch; do alongside A–C.

## Phase 2.5D.1 — Kiosk enter/exit button ✅ (2026-06-25)
- [x] "Enter kiosk" affordance in the web shell sidebar (`<a href="/kiosk">`, full nav into the
      separate kiosk route tree).
- [x] "Exit kiosk" affordance on the kiosk ambient screen (corner link → `/`, stops propagation
      so it doesn't trigger "tap to start").

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
- [ ] Restyle the kiosk to match the **original Meridian kiosk** (needs the legacy reference:
      `~/Documents/new/project-meridian`). Currently hardcoded `bg-gray-*`; move onto the shared
      design tokens so it can theme.
- [ ] Light/dark mode toggle on the kiosk.

---

## Cross-cutting

## Phase 2.5X — Verify & wire together
- [ ] Atlas reminders → appear on Hub widget **and** Calendar with no double-writing (D7).
- [ ] Meridian Hub widget + Calendar Meridian deadlines render for the right roles only.
- [ ] Permissions enforced across all three surfaces (no leaks to children/guests); tests added.
- [ ] `tsc` + production build clean; backend suite green; run the stack on the home server.

---

## Definition of done (Milestone 2.5)

- [ ] **Hub:** shows the right per-user "today" items; households configure (enable/order/size) and
      users hide/reorder; a live **Meridian Hub widget** renders (web + kiosk); the "every node
      ships its widget" pattern is documented and applied.
- [ ] **Atlas:** pleasant and capable for daily list/reminder/checklist use on web and kiosk, with
      Postgres FTS search and dated items flowing to the Calendar.
- [ ] **Calendar:** month/week/day/agenda views, reachable from every page (peek + quick-add),
      configurable, colour-coded, good-looking; shows all permitted node + standalone events with
      no double-writing.
- [ ] Permissions enforced throughout; all three follow the shared design system; used daily on the
      home server.
</content>
