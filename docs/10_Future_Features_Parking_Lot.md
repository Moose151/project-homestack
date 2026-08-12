# Document 10 — Future Features & Parking Lot

> **Canonical future-work register.** This file contains genuinely deferred ideas only. Shipped
> work belongs in the owning specification and `VERSION_HISTORY.md`, not here. Architectural
> decisions D1–D24 live in `00_README_and_Changelog.md`.

## 1. Parking-lot rule

A future idea normally becomes a **feature inside an existing node or core service**, not a new
node. New nodes require the justification in `09_Node_Model_Decision_Record.md`.

Items should be removed from this document when they ship or are promoted into an active roadmap
milestone.

## 2. Deferred infrastructure

Add these only when real operating pressure justifies them:

- **Durable event bus** — D4 deliberately uses the thin in-process events interface today. A
  broker/durable queue is only warranted if reliability/scale requirements outgrow signals.
- **Redis / Celery / Celery Beat** — introduce when background work can no longer be handled
  reliably by the current scheduled management-command pattern.
- **Per-row attachment ACLs** — only if the existing visibility/sensitivity model proves too
  coarse in real use.
- **Production serving hardening** — replace Django `runserver` and the Vite development server in
  the live stack with a production WSGI/static-serving path; reduce direct host port exposure and
  move internal services onto private Docker networking.
- **Automated deployment/CI** — one supported deploy command with backup, build, migration,
  restart and health checks; backend/frontend/production-build/E2E checks in CI.
- **Encrypted off-server backups** — retain the tested HomeStack restore path while adding a
  second encrypted copy outside the primary server/storage device.
- **2FA / passkeys** — particularly for adult/admin accounts before any public exposure.

## 3. Current active platform expansion

**PWA / Web Push notifications** are the active follow-up now that trusted LAN HTTPS exists. The
canonical design is `32_Core_Notifications_and_Push.md`; do not duplicate its implementation plan
here. Native-app push and email notification channels remain future work.

**Home Assistant** is not parked: it is the next important dedicated integration milestone after
push notifications, governed by D22 and `26_Node_Home_Assistant.md`.

## 4. Deferred features by existing domain

### Atlas

- rich text/Markdown notes;
- reusable list/templates and recurring-list workflows;
- voice capture;
- smarter grocery assistance once Hearth exists.

Grocery, Shopping, Agenda, appointments/events browsing and birthday/People coordination have
already shipped and must not be listed as future work.

### Home Wiki / household guide

- page revision history;
- stronger linked-page/procedure blocks;
- house-sitter/emergency presentation modes;
- possible future presentation as a Homestead capability rather than separate top-level
  navigation, if the proposed consolidation is actually approved and implemented.

### Pets

- feeding schedules;
- food/inventory integration;
- weight trends;
- deeper insurance/document workflows;
- house-sitter mode;
- Meridian-generated pet chores.

### Education

- richer grades/progress analytics;
- study timers;
- reading logs;
- term/import helpers;
- deeper school-age child/kiosk workflows where they add real value;
- Meridian homework/task integration.

### Homestead

- portable floor-plan **builder/editor** for other households (the current installation already
  has a native interactive plan for this house);
- revision/draft support for editable plans;
- deeper document/warranty linkage;
- richer long-term maintenance templates;
- productized onboarding for an unknown household rather than assumptions from a supplied plan.

The pool schedule editor, utility usage, room plans, linked floor-plan spaces and household cost
integration have already shipped.

### Inventory / Stock & storage

Do not automatically create a new top-level node. The current proposal is an optional Homestead
capability. Potential scope:

- consumables and stored-item inventory;
- low-stock/expiry views;
- barcode/QR labels;
- storage locations/boxes;
- pantry linkage to Hearth/Atlas Grocery.

### Assets & vehicles

The home-appliance/warranty scope already belongs to Homestead. Remaining possible non-home scope:

- vehicles;
- tools and high-value owned items;
- odometer/service/registration reminders;
- insurance and warranty claims;
- service-cost history;
- QR labels.

Prefer a protected Homestead capability unless actual use demonstrates that this is a major
independent domain.

### Hearth

A significant remaining everyday-life gap:

- recipes and safe recipe import;
- meal planning/calendar;
- "what's for dinner" household view;
- ingredient scaling;
- leftovers/batch cooking;
- optional nutrition;
- generation of missing ingredients into **Atlas Grocery**, not a competing grocery database.

### Travel

The core trip, booking/cost and itinerary/Things-to-do workflow is shipped. Remaining possible
slices:

- packing lists;
- protected travel documents;
- richer galleries/journal;
- maps/weather/live-flight information;
- external booking APIs;
- currency conversion;
- pet/home-care handoff;
- deeper Solace travel-budget integration.

### Projects

Do not add a top-level Projects node without evidence. Homestead owns home projects, Travel owns
trips and Atlas covers lightweight general work. Reconsider only if real cross-domain projects need
Kanban/dependencies/templates/budget/photo-progress workflows that do not fit those owners.

### Health

This remains intentionally deferred because of its sensitivity. Possible scope includes:

- appointments/providers;
- medications/prescriptions;
- allergies/immunisations;
- medical notes/documents;
- health trends;
- emergency health card;
- stronger encryption requirements where justified.

Medical Health must remain separate from the shipped social **Fitness & Training** node (D24).

### Meridian

Potential polish rather than a new architecture:

- additional challenge/task templates;
- richer weekly summaries;
- optional evidence/photo workflows where useful;
- further child-facing delight only when real use asks for it.

### Solace / Money

Potential additions:

- richer reports/exports;
- tighter links to future Hearth/Travel/vehicle planning where ownership remains clear;
- encrypted finance fields only if the threat model justifies the complexity.

### Fitness & Training

Potential additions:

- rest timers;
- RPE/RIR;
- scheduled training-day planning;
- running/swimming pace splits;
- trend charts and deeper progression analytics.

These are optional enhancements, not blockers for the existing Fitness node.

### People / Corners

- optional comments/help offers beyond current bounded reactions where privacy rules remain clear;
- further household member summaries only when they can be projected safely from source records.

## 5. Future platform features

- native Android/iOS application;
- desktop application;
- fuller offline mode and conflict handling;
- email notifications;
- external calendar sync;
- OCR and document extraction;
- semantic/AI-assisted search;
- general plugin framework only if multiple real integrations demonstrate the need;
- general-purpose webhooks/automation only after the Home Assistant bridge proves the narrower
  event/control pattern.

A PWA is the current first mobile bridge; native-client technology remains deliberately undecided.

## 6. Delight / low-priority ideas

**Node graph view.** An Obsidian-style visual map of HomeStack domains and their declared
publish/consume relationships could be useful as an exploratory architecture/product view. It is
not operationally important and should wait until core reliability and daily-use work is mature.

## 7. Explicitly out of scope

These are not "later" items:

- SaaS hosting/multi-household tenancy;
- building a second source of truth for Calendar/Hub/Corners;
- arbitrary cross-node model imports;
- a generic integration/plugin layer merely to connect Home Assistant;
- uncontrolled public exposure of the home server.

If HomeStack is released, it remains self-hosted with one household per installation unless a new
explicit product decision replaces D1/D2.

## 8. Review rule

Before promoting a parked idea, ask:

1. Is this solving a real household problem observed in use?
2. Does an existing domain already own the data/workflow?
3. Can it reuse current permissions, Calendar, notifications, attachments and events boundaries?
4. Is the operational/security cost justified?
5. If proposing a new node, would it still make sense as an independently useful household domain?

If those answers are weak, leave it parked.