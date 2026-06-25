# Core Spec — Hub

> Canonical. **Core service, not an opt-in node.** The Hub ships in every install and cannot be
> disabled. Global rules from `00_README_and_Changelog.md` apply: base-model inheritance where
> records are household data, central permission resolver + visibility mixin (D10), node
> decoupling via the `events` signal interface (D4 — the Hub never imports another node's
> models), people-vs-users rule (D12), shared design system. The Hub **owns no household
> content of its own** — it is a read-mostly aggregation and presentation surface over other
> nodes and core services.

## 1. Purpose

The Hub is HomeStack's landing surface — the first screen on web and the post-login screen on
kiosk. It answers one question: ***"What needs attention today?"*** It pulls the most relevant,
permitted, time-sensitive items from across enabled nodes (Atlas reminders and to-dos, Meridian
tasks, upcoming Calendar events, Home Wiki favourites, notifications, …) into one configurable,
permission-aware dashboard so the household never has to open each node to know what matters.

## 2. Philosophy

The Hub is a **window, not a store**. It never owns domain data; every card is sourced from a
node or core service and rendered through a widget. Configurable but calm: each household and
each user tailors which widgets show, in what order and size, but the default is a quiet,
glanceable "today" view. It is **not** the Calendar (the full timeline lives in `scheduling`),
**not** a notification centre (that's Notifications), and **not** a node — it has no opt-in
toggle and no node-specific business logic.

## 3. What belongs on the Hub

Today/soon items that need a human's attention: reminders due, my to-dos, household shopping
list, today's Meridian tasks and points summary, upcoming calendar events, Home Wiki favourites
and emergency shortcut, unread notification summary, quick-add/quick-capture, greeting + date.
Each is a **widget** backed by a node or core service.

## 4. What does NOT belong on the Hub

Full node UIs (open the node), the complete calendar (Calendar view), the full notification log
(Notifications), any data the Hub would "own". The Hub never persists domain records, never
writes `calendar_events`, never re-implements a node's logic, and never bypasses the resolver to
show something a user shouldn't see.

## 5. Primary users

Admins, managers, users, permitted child accounts, kiosk users. Every authenticated session
lands on a Hub. Child and kiosk sessions get a simplified, kiosk-safe widget set only
(`supports_kiosk = True`).

## 6. Key features

**Widget catalogue (`HubWidget`)** — the global, seeded list of available widget types. Each
has `key`, `name`, `description`, optional `source_node` (FK → `nodes.Node`, null for core
widgets), `supports_kiosk`, `display_order`. Adding a widget to HomeStack = seeding a row +
providing its data via a selector. Seeded today: `atlas_todos`, `atlas_reminders` (both
kiosk-safe); the Meridian/Calendar/Home Wiki widgets are added by their respective nodes.

**Household configuration (`HouseholdHubWidget`)** — which catalogue widgets the household has
enabled, plus per-household `display_order`, `size` (small/medium/large) and `settings_json`.

**Per-user overrides (`UserHubWidget`)** — a user may hide or reorder widgets for their own Hub
(`is_enabled`, `display_order`, `settings_json`) without affecting other members.

**Resolution** — at request time the Hub composes: catalogue → household-enabled → user
overrides → (kiosk filter) → each widget's selector runs **permission-filtered** for the
current user → assembled, ordered widget payloads.

**Kiosk mode** — `GET /hub/kiosk/` returns only `supports_kiosk = True` widgets, simplified for
touch and children.

**Quick add / quick capture** — foundational: rapid add of a note/list-item/reminder/to-do from
the Hub, delegating to the owning node's services (richer later).

**Ambient / utility widgets (non-node)** — not every widget is backed by a node. The Hub can
also host standalone "ambient" widgets that make it feel like a home dashboard / family
noticeboard rather than just a task list. These are `HubWidget` rows with `source_node = null`
and their own small payload/settings (`settings_json`), no domain data of their own. Candidates:
- **Clock** — time + date, configurable format/timezone (kiosk-safe; a natural ambient-screen
  element).
- **Weather** — local conditions + short forecast. Needs an external data source, so it's the
  one ambient widget that implies new infra (an outbound API call / API key in `settings_json`,
  caching). Park until that's wanted; respects "no infra before a feature needs it" (D5).
- **Photo / family slideshow** — rotating household photos via the shared attachment service
  (kiosk-friendly noticeboard feel; permission/sensitivity aware).
- **Greeting / on-this-day / quote / countdown** — small delight widgets (e.g. "12 sleeps until
  the holiday").
These follow every Hub rule: seeded catalogue row, permission- and kiosk-filtered, own no domain
data, write no calendar rows. Most are local/offline; **weather is the exception** (external
fetch) and is explicitly parked until requested.

## 7. Permissions

Resource: `hub` (`hub.view`). Access to the Hub surface itself is broad (all authenticated
roles), but **each widget's contents are resolved through the central resolver + visibility
mixin (D10)** against the requesting user — a child never sees a widget or item they aren't
permitted, even if the household enabled it. No ad-hoc permission checks in the Hub view; the
view is thin and delegates to `hub.services.get_hub_widgets(user, kiosk_mode=…)`.

## 8. Node integration (how nodes contribute widgets)

A node contributes to the Hub by: (1) seeding a `HubWidget` row with `source_node` set and
`supports_kiosk` as appropriate; (2) exposing a selector that returns its widget payload,
already permission-filtered; (3) the Hub service calling that selector during resolution. The
Hub **never imports node models** — it reads through the node's selector / the events interface
(D4). Disabling a node hides its widgets automatically.

## 9. Calendar integration

The Hub **reads** upcoming events from `scheduling` for an "upcoming events" widget; it **never
writes** `calendar_events` and never owns dates (D7). Dated items shown on the Hub are owned by
their node and surfaced via the scheduling helper.

## 10. Notifications

The Hub may show an unread-notifications **summary** widget (count + most recent), reading from
the Notifications service. The full list and read/mark-all actions live in Notifications, not
the Hub.

## 11. Events (signals)

The Hub is primarily a **consumer/aggregator** and is intentionally lightweight on the bus. It
does not need to subscribe to node events for V1 (it composes live at request time via
selectors). Future: cache/invalidate widget payloads in response to node events
(`*_created/_completed/_due`) once performance demands it (D5 — not before).

## 12. Search

The Hub has no search of its own; search is global (`search`, Postgres FTS, D9). The Hub may
host a search entry point/quick-link widget that hands off to global search,
permission-filtered.

## 13. Attachments

None. The Hub stores no files. Widgets that reference attachments link to the owning node's
records via the shared attachment service.

## 14. Kiosk

The post-PIN kiosk dashboard **is** a Hub (`GET /hub/kiosk/`): large widget cards, only
kiosk-safe widgets, simplified for children, minimal typing, clear visual states, touch-first,
inactivity timeout back to avatar select. Today's kiosk Hub renders the Atlas to-dos and
reminders widgets; Meridian task/celebration cards are added by Meridian's kiosk widgets.

## 15. Mobile / web

Web: greeting + date header, responsive widget grid (size-aware), quick-add button, sensible
defaults, dark-mode aware, large tap targets. Per-user hide/reorder. Offline parked.

## 16. Progressive detail

Basic: default widget set, glanceable today view. Standard: household enable/disable, order and
size per household, kiosk-safe subset. Detailed: per-user hide/reorder, per-widget settings
(`settings_json`), quick-add, future drag-and-drop layout and cached payloads.

## 17. Data model

`hub_widgets` (`HubWidget`: `key` unique, `name`, `description`, `source_node` FK nullable,
`supports_kiosk`, `display_order` — **catalogue/seed data, plain model, not household-scoped**).
`household_hub_widgets` (`HouseholdHubWidget`: `household` FK, `widget` FK, `is_enabled`,
`display_order`, `size`, `settings_json`; unique `(household, widget)`).
`user_hub_widgets` (`UserHubWidget`: `user` FK, `widget` FK, `is_enabled`, `display_order`,
`settings_json`; unique `(user, widget)`).

The Hub holds **only configuration** — no domain records. Widget *contents* are always fetched
live from the owning node's selectors. Shared services used: permissions resolver, scheduling
(read), notifications (read), each node's selectors.

## 18. API

`GET /api/v1/hub/` — assembled, permission-filtered, ordered widgets for the current user (web).
`GET /api/v1/hub/kiosk/` — same, filtered to `supports_kiosk = True`, simplified for kiosk.
Both delegate to `hub.services.get_hub_widgets(user, kiosk_mode)`. Widget enable/order/size
configuration endpoints (household + per-user) are the next API surface (parked until the
Atlas + Hub UX pass).

## 19. V1 scope

Widget catalogue + seed · household enable/order/size · per-user hide/reorder · permission-aware
resolution · kiosk-safe subset · web Hub + kiosk Hub · Atlas to-dos/reminders widgets live ·
node-contributed widgets (Meridian/Calendar/Home Wiki) as those nodes land. **Not in V1:**
drag-and-drop layout editor, cached/event-invalidated payloads, AI "smart" prioritisation,
cross-household templates, ambient/utility widgets (clock/photo/greeting are low-effort and
local; **weather** needs an external data source + caching and is parked until requested — D5).

## 20. Risks & mitigation

Risk: the Hub becoming a second home for node logic, leaking unpermitted content, or growing
slow as nodes multiply. Mitigation: strict read-only aggregation (owns no data, writes no
calendar); every widget payload runs through the resolver/visibility mixin; nodes contribute via
selectors/events only (no cross-imports, D4); defer caching until measured need (D5); keep the
default view calm and kiosk-safe by default.

## 21. Completion criteria

The Hub shows the right "today" items per user and per role; households enable/disable, order and
size widgets; users hide/reorder their own; kiosk shows only kiosk-safe widgets simplified for
children; every widget is permission-filtered (no leaks to children/guests); Atlas and
node-contributed widgets render live; the Hub owns no domain data and writes no calendar rows;
follows the shared design system.
</content>
</invoke>
