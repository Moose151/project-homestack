# Node Spec — Projects

> **Status:** evidence-gated future domain, not an automatic roadmap commitment. Homestead already
> owns home/room improvements, Travel owns trips, and Atlas covers lightweight general planning.
> Create a top-level Projects node only if real cross-domain initiatives demonstrably need richer
> project workflows that do not fit those owners.

## 1. Why this spec still exists

HomeStack may eventually need a domain for genuinely large, cross-domain initiatives with enough
structure to justify their own lifecycle, tasks, milestones, files and coordination.

This document preserves that possible boundary without authorising implementation merely because a
Projects node appeared in early plans.

## 2. Current ownership before Projects exists

Use the existing owner when it fits:

- **home renovations/room upgrades/repairs/home improvements** → Homestead;
- **trips/holidays/travel planning** → Travel;
- **ordinary household to-do/checklists/planning** → Atlas;
- **rewarded work** → Meridian;
- **financial set-asides/bills/purchase planning** → Solace;
- **durable household instructions/reference** → Home Wiki.

Do not move existing Homestead/Travel/Atlas records into a speculative Projects domain just to make
the architecture look symmetrical.

## 3. Evidence required to create the node

A top-level Projects domain becomes justified only when real household use repeatedly needs several
of the following across non-home/non-travel initiatives:

- project-specific lifecycle/status independent of a room/trip/list;
- multiple workstreams or task groups;
- dependencies/milestones;
- substantial notes/files/history around one initiative;
- progress tracking/Kanban-like planning;
- project-level budget references to Solace without Solace becoming project management;
- several People coordinating work over weeks/months;
- reusable project templates;
- photo/progress history;
- meaningful Hub/Calendar/Search behavior unique to projects.

One isolated complex list is not enough justification.

## 4. Possible future ownership boundary

If approved, Projects would own **general cross-domain initiative structure**, not the domain facts
produced by the initiative.

For example:

- a project can reference a Solace budget/purchase but does not own payment history;
- a completed project can link to an asset/home record but does not become the asset/property owner;
- project tasks can project into Calendar but remain project-owned;
- attachments use the shared file service;
- rewarded versions of a task can be linked through Meridian without copying the project task into
  Meridian as the only source of truth.

## 5. Candidate model

Only if the node is approved, a small initial model might include:

### Project

- title/description;
- lifecycle/status;
- category;
- start/target date;
- owner Person;
- visibility;
- optional links to related domain records.

### Project task

- project;
- title/description;
- assigned Person;
- due date;
- priority/status/order;
- source-linked Calendar projection.

### Notes / milestones

Add only when the first approved workflows need them. Do not prebuild a full project-management
suite.

## 6. Permissions

Follow central role/visibility rules. A project's visibility must not grant access to linked
financial, Health or other sensitive domain records.

Cross-domain summaries always re-check the linked source's permissions.

## 7. Hub / Calendar / Notifications

If implemented, possible projections include active projects, tasks/milestones due and assigned
work.

Dates follow D7; notifications use the shared system; no project-specific scheduler/push mechanism.

## 8. Events and integrations

Use D4 events/shared services for cross-domain reactions. Do not import Solace/Homestead/Assets/
Meridian models into Projects or vice versa.

A project completion event can invite another domain to create/update its own record, but the
receiving domain remains the owner of that result.

## 9. Search / mobile / kiosk

Search operates on permission-filtered Projects data only after the node exists.

Responsive web would be the primary project-management surface. Kiosk should show only simple
permitted assigned work/countdowns if useful rather than a full board.

## 10. Decision rule

Before starting Projects, document at least two or three real household initiatives that the
existing Homestead/Travel/Atlas owners cannot represent cleanly and show what shared project
capability they require.

If that evidence is absent, keep this node unimplemented and improve the existing owner instead.