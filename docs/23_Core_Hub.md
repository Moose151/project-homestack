# Core Spec — Hub

> **Status:** shipped core service and daily landing surface. Hub is always present, is not an
> opt-in node, and owns no household domain records. It aggregates permitted information from core
> services and enabled domains.

## 1. Purpose

Hub answers: **What needs attention today?**

It provides one calm, configurable household landing page containing the most useful permitted
summaries and actions without requiring a person to open every domain individually.

Hub is:

- a read-mostly aggregation surface;
- configurable per household and per User;
- permission-aware;
- responsive on phone/desktop;
- capable of a simplified kiosk-safe presentation.

Hub is **not** Calendar, Notifications, Search or a second copy of any node's data.

## 2. Ownership rule

Hub stores only widget catalogue/configuration state. Widget content remains owned by the source
domain/core service.

A Hub card must never become the only copy of a task, event, bill, reminder, workout, trip or other
household fact.

Derived content is assembled after permission/visibility filtering. If the source becomes hidden,
locked, deleted or inaccessible, Hub must stop revealing it.

## 3. Widget model

The established configuration families are:

- **`HubWidget`** — global catalogue/seed row describing a widget type, optional source node,
  kiosk support and default order;
- **`HouseholdHubWidget`** — household enablement/order/size/settings;
- **`UserHubWidget`** — per-User hide/order/settings overrides.

The exact fields are defined by current Django models/migrations.

The effective widget set resolves approximately as:

```text
widget catalogue
 -> enabled node/core availability
 -> household configuration
 -> User overrides
 -> kiosk-safe filter when applicable
 -> source selector/content provider
 -> permission/visibility filtering
 -> ordered payload
```

## 4. Current configuration UX — shipped

Household/admin configuration and per-User customization are part of the current product, not a
future V1 placeholder.

The implemented UI/API supports the current combination of:

- household widget enable/disable;
- order;
- size;
- per-User hide/reorder;
- responsive/keyboard-friendly ordering controls;
- optimistic updates where supported;
- atomic/effective ordering behavior rather than requiring a separate page refresh for every move.

Do not document widget configuration as "the next API surface" again; exact routes live in the Hub
URLconfs/tests.

## 5. What belongs on Hub

Useful glanceable/today-oriented examples include:

- Atlas to-dos/reminders and quick capture;
- Calendar upcoming/today items;
- Meridian task/reward/points summaries;
- Education deadlines/events;
- Pets care/appointments;
- Homestead maintenance/home attention;
- Solace/Money information only for Users with the required finance access/elevation contract;
- Fitness recent/training summary where useful;
- Travel countdown/booking attention;
- Home Wiki favourites/emergency shortcuts;
- Notifications summary;
- small core/ambient widgets such as clock, greeting/quote/countdown where implemented.

A shipped node does **not** need a Hub widget merely to prove it is a valid node. Books currently
has no requirement to invent a widget if personal shelves/Book Clubs do not produce meaningful
"needs attention today" information. Add a Books widget only for a real useful workflow.

## 6. What does not belong on Hub

- full domain management screens;
- the complete Calendar;
- the full Notifications history;
- unrestricted Search results;
- duplicate persisted copies of source records;
- sensitive information that would not be visible in the owning domain;
- speculative widgets added only because every node is expected to have one.

## 7. Permissions (D10)

Hub surface access is broad for authenticated household Users, but each widget and each returned
item must respect its source security boundary.

Rules:

- run source content through permission-aware selectors/services;
- filter sensitive/private records before titles/counts/snippets are assembled;
- node enablement/visibility is respected;
- a child/kiosk User never gains content because an adult enabled the widget globally;
- sensitive-node locked state must not leak bill names/amounts/health detail through Hub;
- frontend hiding is not authorization.

Avoid ad-hoc permission checks in the Hub view. Keep request handlers thin and central/source
selectors authoritative.

## 8. Node/core integration (D4)

A domain may contribute Hub content by registering/seeding a widget and exposing a bounded content
provider/selector through the established Hub integration pattern.

Hub must not import another node's models simply to query its data. Use the existing decoupled
service/selector/event boundary.

If a node is disabled, its widgets disappear without deleting the node's underlying data.

## 9. Calendar

Hub may read upcoming permitted events from `scheduling` but never writes Calendar rows.

A dated Hub item links to the Calendar-owned or node-owned source according to D7. Hub does not
create another editable deadline/date field.

## 10. Notifications

Hub can show an unread/recent notification summary. The Notifications service owns notification
state and Web Push delivery/preferences.

Push implementation belongs to `32_Core_Notifications_and_Push.md`; Hub may provide a shortcut or
summary but must not manage device subscriptions itself.

## 11. Quick actions

Quick capture/add actions are useful when they delegate immediately to the owning domain service.

Examples:

- Atlas note/to-do/reminder;
- permitted simple source-specific actions exposed deliberately by a widget.

Do not implement broad cross-domain write logic inside Hub merely for convenience.

## 12. Ambient / utility widgets

Non-domain widgets can exist with `source_node = null` where they make the household dashboard more
useful or pleasant.

Current/local examples can include clock, greeting/quote and countdown behavior. A countdown stores
an explicit target date/time; date-only entry should use/explain a consistent household-local
fallback rather than silently depend on server timezone.

Future external-data widgets such as weather should be added only with a clear provider/cache/
secret/failure strategy. Do not add infrastructure merely to fill visual space.

## 13. Search

Hub has no independent search database. The global Search service owns search aggregation. Hub can
host/open the global Search interaction.

## 14. Attachments

Hub stores no files. A widget can reference an owning record/attachment only through the shared
protected attachment/source route.

## 15. Kiosk

The kiosk post-login dashboard uses the Hub concept but requests/renders only kiosk-safe content.

Kiosk rules:

- large cards/touch targets;
- minimal typing;
- current Person/User context clear;
- only widgets explicitly safe for kiosk;
- automatic session timeout/return to avatar selection;
- no finance/Health/protected document leakage.

A node with `supports_kiosk=False` remains absent; Hub does not override the node's surface contract.

## 16. Responsive web

Phone and desktop use the same product hierarchy with different density:

- clear greeting/date/current-person context;
- responsive size-aware grid;
- fast common actions;
- per-User hide/reorder controls that remain accessible without drag-and-drop;
- loading/error/empty state per widget where practical so one failing source does not make the whole
  Hub unusable.

## 17. Performance and failure isolation

Hub can become expensive because it aggregates many domains.

Rules:

- do not add caching/brokers before measurement (D5);
- source failures should degrade their widget instead of blocking unrelated content where possible;
- use existing server timing/slow-request evidence before optimizing;
- avoid repeated expensive source reconciliation within the same request when an owning domain
  already provides a request-scoped/cache-safe solution;
- if future caching is introduced, it must preserve permission/user/node configuration boundaries.

## 18. API contract

Exact current route names are defined by Hub URLconfs/tests. Major API concepts are:

- assembled web Hub payload;
- kiosk-safe Hub payload;
- household widget configuration;
- per-User widget overrides/order/settings.

Do not maintain another obsolete endpoint inventory in this spec.

## 19. Data ownership

Hub-owned persistent data is configuration/catalogue only. Domain payloads are computed/read from
their owners.

That invariant allows a source record to be corrected once and immediately appear correctly in Hub,
Calendar, Search, Corners and Notifications without synchronized copies.

## 20. Completion state

Hub's current useful baseline is shipped:

- configurable widget catalogue;
- household and per-User customization;
- permission-aware resolution;
- responsive web Hub;
- kiosk-safe subset;
- quick capture and useful core/domain summaries;
- ambient/delight widgets already implemented where appropriate.

Future Hub work should be driven by observed relevance/performance/UX needs, not by a rule that every
node must contribute a widget.