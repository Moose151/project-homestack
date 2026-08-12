# Document 9 — Node Model Decision Record

> Canonical. Records why HomeStack uses a small set of broad domains and distinguishes what is
> **shipped** from what is merely **planned/evidence-gated**. Cross-cutting decisions live in
> `00_README_and_Changelog.md` (D1–D24).

## 1. Decision

HomeStack uses a **small, deliberate set of broad nodes** rather than many small overlapping
ones. Nodes are major household domains with their own workflows/data/privacy boundaries; small
features normally belong inside an existing node or shared core service.

### Core platform services

Hub · Calendar (`scheduling`) · People · Notifications · Search · Documents/Attachments ·
Permissions · Settings · Backups · Audit.

The durable Event Bus listed in early drafts is **not a core service**. Node interaction uses the
thin internal signal/event interface described by D4.

### Shipped opt-in domains

Atlas · Meridian · Education · Home Wiki · Pets · **Books** · Homestead · Solace/Money ·
Fitness & Training · Travel.

Books is intentionally listed here: it is a real seeded opt-in node with personal reading shelves
and shared book clubs. Older node-model documentation omitted it even though the implementation
already existed.

### Important planned domain

- **Home Assistant** — dedicated bounded bridge (D22), sequenced after Web Push.

### Deferred / evidence-gated domains or capabilities

- **Hearth** — likely future everyday domain for recipes/meal planning; uses Atlas Grocery.
- **Health** — future sensitive medical domain, deliberately later than Fitness.
- **Inventory / Stock & storage** — proposed Homestead capability rather than automatically a
  top-level node.
- **Assets & vehicles** — remaining non-home asset/vehicle scope; proposed Homestead capability
  unless real use proves an independent node is needed.
- **Projects** — evidence-gated; do not implement while Homestead/Travel/Atlas already own the
  actual household workflows.

`31_Core_Manage_HomeStack.md` also contains a future proposal to present Home Wiki as a Homestead
**Household guide** capability. That is not implemented and does not erase the current Home Wiki
node/data model.

## 2. Reason

HomeStack is intentionally broad but should not feel fragmented. Too many nodes create confusing
navigation, duplicated records, overlapping permissions, more maintenance, a poorer kiosk
experience and unclear ownership.

The node model therefore optimises for:

- one clear source of truth per household concept;
- shared core services for cross-cutting behaviour;
- predictable privacy and permission boundaries;
- a navigation model ordinary household members can understand;
- enough separation that genuinely independent domains can evolve cleanly.

A node's existence is justified by the workflow, not by the desire to make every data type a menu
entry.

## 3. Current ownership decisions

- Home property, rooms, appliances, warranties, household services, maintenance, pools/spas and
  home improvements → **Homestead** (D21).
- Household finance, bills/subscription-style recurring costs and budgeting → **Solace/Money**.
- General notes, to-dos, Grocery, Shopping, reminders and lightweight coordination → **Atlas**.
- Personal reading shelves, book ratings and shared book clubs → **Books**.
- Structured school/university study → **Education**.
- Rewarded household tasks/routines/points/rewards → **Meridian**.
- Persistent household procedures/reference knowledge → **Home Wiki**.
- Pet profiles/treatments/appointments → **Pets**.
- Social training programs, workouts and performance records → **Fitness & Training** (D24).
- Trip ideas, bookings/cost planning and itinerary → **Travel**.
- Documents/attachments → shared core file service, linked back to owning records rather than
  copied into each node.
- People → shared core service.
- Diagnoses, medications, medical/injury records and other sensitive human health information →
  future **Health**, with a stronger privacy boundary than Fitness.
- Smart-home status and safe controls → future dedicated **Home Assistant** bridge (D22); Home
  Assistant remains the device/state/history/automation source of truth.

## 4. Books boundary

Books is a valid independent domain despite early docs forgetting it because it has durable,
independently useful workflows that do not fit Atlas or Education cleanly:

- one shared Book catalogue;
- per-User Want to Read / Reading / Read shelves;
- per-User rating/notes for a Book;
- household Book Clubs and membership;
- club backlog/reading/history and ordered up-next queue;
- URL/ISBN enrichment through the shared safe Link Import capability.

Education may reference Books for structured course reading later, but should not own personal
reading history or club workflows. Atlas may hold a shopping wish for a physical book, but should
not become the reading tracker.

## 5. Capability-consolidation position

The product can reduce navigation without merging ownership blindly.

Current proposals:

- Stock & storage inside Homestead;
- Assets & vehicles inside Homestead;
- Household guide presentation inside Homestead.

These are **presentation/capability proposals**, not permission to delete current records or claim
the capabilities are already implemented. Any consolidation must preserve stable source ownership,
permissions, Search/Hub behavior and links.

Books is not currently part of that consolidation decision. If its navigation is ever reconsidered,
its personal shelves, clubs, queue and ratings must remain intact rather than being flattened into
Atlas or Education merely to reduce menu count.

## 6. Rule for future nodes

A new node is justified only when it clearly satisfies most of these conditions:

1. It is a major household domain, not a single feature.
2. It has durable records/workflows of its own.
3. It needs a meaningfully distinct permission/privacy boundary or user mental model.
4. It contributes independently to Hub/Calendar/Search or another major platform surface.
5. Putting it in an existing node would make ownership or UX materially worse.
6. It would be independently useful to other households.
7. Real household use demonstrates the need rather than the idea only being theoretically neat.

If those conditions are not met, keep the feature in an existing node or core service.

## 7. Meridian and Solace position (D13/D14)

Meridian and Solace are **native HomeStack nodes**, not iframe/external-link integrations. Their
proven business rules were reused while their shells/data models were rebuilt around shared
HomeStack Users/People, permissions, Calendar, Hub, audit and backup services.

Import tooling may exist for migration, but a household is not required to use it. The live
HomeStack household chose to enter Solace data fresh rather than make the legacy import part of
its cutover path.

## 8. Fitness and Health boundary (D24)

Fitness & Training is a shipped, separate node because its normal household-sharing model is
fundamentally different from medical Health.

Fitness owns programs/training days, live/completed workouts, exercises/sets and athletic
performance records.

Health owns sensitive medical information such as diagnoses, medications, injuries as medical
records, clinical/body measurements and medical notes. Do not move medical data into Fitness to
avoid Health's stronger controls.

## 9. Home Assistant exception (D22)

Home Assistant is the deliberate exception to treating an external system as a generic
integration. Its local-device workflow, permission/safety boundary and Hub value justify a
dedicated bridge.

It stores HomeStack presentation/control/event mappings only. Home Assistant continues to own
devices, entity state, history, areas and automations. HomeStack continues to own household
records, People, tasks, Calendar data, permissions and audit.

This does **not** authorise a generic `integrations` app, plugin framework or iframe layer.

## 10. Final position

HomeStack grows through deliberate capability expansion, not accidental node sprawl. The current
shipped catalogue already covers a wide portion of household life; reliability and depth are more
valuable than inventing another node for every new feature.