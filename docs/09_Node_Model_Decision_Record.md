# Document 9 — Node Model Decision Record

> Canonical. Supersedes earlier versions. Records *why* HomeStack uses the node set it does.
> Cross-cutting build/architecture decisions live in `00_README_and_Changelog.md` (D1–D24).

## 1. Decision

HomeStack uses a **small, deliberate set of broad nodes** rather than many small overlapping
ones. Nodes are major household domains with their own workflows/data/privacy boundaries; small
features normally belong inside an existing node or shared core service.

### Core platform services

Hub · Calendar (`scheduling`) · People · Notifications · Search · Documents/Attachments ·
Permissions · Settings · Backups.

The durable Event Bus listed in early drafts is **not a core service**. Node interaction uses the
thin internal signal/event interface described by D4.

### Current/confirmed node catalogue

Atlas · Home Wiki · Pets · Education · Inventory · Assets · Hearth · Travel · Projects · Health ·
Meridian · Solace · Homestead · Home Assistant · Fitness & Training.

This catalogue does **not** mean every listed node must remain a permanent top-level navigation
entry. `31_Core_Manage_HomeStack.md` contains an explicit future proposal to consolidate some
capabilities (notably Stock & storage / Assets & vehicles / Household guide) into Homestead while
preserving their data and behaviour. That proposal is not implemented merely because it is
written down.

## 2. Reason

HomeStack is intentionally broad but should not feel fragmented. Too many nodes create confusing
navigation, duplicated records, overlapping permissions, more maintenance, a poorer kiosk
experience and unclear ownership.

The node model therefore optimises for:

- one clear source of truth per household concept;
- shared core services for cross-cutting behaviour;
- predictable privacy and permission boundaries;
- a navigation model ordinary household members can understand;
- enough separation that sensitive or specialist domains can evolve independently.

## 3. Current consolidation decisions

- Home property, rooms, appliances, warranties, household services, maintenance, pools/spas and
  home improvements → **Homestead** (D21).
- Household finance, bills, subscriptions and budgeting → **Solace/Money**.
- General notes, to-dos, Grocery, Shopping, reminders and lightweight coordination → **Atlas**.
- Documents/attachments → shared core file service, linked back to owning records rather than
  copied into each node.
- People → shared core service.
- Social training programs, workouts and performance records → **Fitness & Training** (D24).
- Diagnoses, medications, medical/injury records and other sensitive human health information →
  **Health**, with a stronger privacy boundary than Fitness.
- Smart-home status and safe controls → dedicated **Home Assistant** bridge (D22); Home Assistant
  remains the device/state/history/automation source of truth.
- Home appliances already belong to Homestead; broader non-home vehicles/tools/owned items remain
  future Assets scope unless the capability-consolidation proposal supersedes it.
- Projects should not become a catch-all for work already owned by Homestead, Travel or Atlas.

## 4. Consequences

**Positive:** cleaner navigation, easier permissions, less duplication, stronger source-of-truth
rules, easier responsive/kiosk design and better long-term maintainability.

**Trade-offs:** some domains are deliberately broad. The solution is clear internal capability
boundaries and good navigation, not automatically splitting them into more top-level nodes.

## 5. Rule for future nodes

A new node is justified only when it clearly satisfies most of these conditions:

1. It is a major household domain, not a single feature.
2. It has durable records/workflows of its own.
3. It needs a meaningfully distinct permission/privacy boundary.
4. It contributes independently to Hub/Calendar/Search.
5. Putting it in an existing node would make ownership or UX materially worse.
6. It would be independently useful to other households.

If those conditions are not met, keep the feature in an existing node or core service.

## 6. Meridian and Solace position (D13/D14)

Meridian and Solace are **native HomeStack nodes**, not iframe/external-link integrations. Their
proven business rules were reused while their shells/data models were rebuilt around shared
HomeStack Users/People, permissions, Calendar, Hub, audit and backup services.

Import tooling may exist for migration, but a household is not required to use it. The live
HomeStack household chose to enter Solace data fresh rather than make the legacy import part of
its cutover path.

## 7. Fitness and Health boundary (D24)

Fitness & Training is a shipped, separate node because its normal household-sharing model is
fundamentally different from medical Health.

Fitness owns:

- programs and training days;
- live/completed workouts;
- exercises and sets;
- running/swimming/strength performance;
- social/household training visibility where permitted.

Health owns sensitive medical information such as diagnoses, medications, injuries as medical
records, body/clinical measurements and medical notes. Do not move medical data into Fitness to
avoid Health's stronger controls.

## 8. Home Assistant exception (D22)

Home Assistant is the deliberate exception to treating an external system as a generic
integration. Its local-device workflow, permission/safety boundary and Hub value justify a
dedicated bridge.

It stores HomeStack presentation/control/event mappings only. Home Assistant continues to own
devices, entity state, history, areas and automations. HomeStack continues to own household
records, People, tasks, Calendar data, permissions and audit.

This does **not** authorise a generic `integrations` app, plugin framework or iframe layer.

## 9. Final position

HomeStack grows through deliberate capability expansion, not accidental node sprawl. Before
creating a new node, first prove why the feature cannot live coherently inside the current model.
