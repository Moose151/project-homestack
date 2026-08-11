# Core Spec — Manage HomeStack and In-app Guides

> **Implementation status (v0.34.0):** node summaries, guides for enabled and disabled nodes,
> dismissible contextual links and generated offline version history are shipped. The capability
> consolidation in §4 remains documented only and was deliberately excluded from implementation.
> This is a core management surface,
> not a new node. It explains releases and enabled capabilities without duplicating node data or
> turning Settings into a technical administration console.

## 1. Outcome

Manage HomeStack should answer three ordinary questions: **What can HomeStack do? What have I
enabled? What changed in this version?** A first-time household can learn the system inside the
app, while an experienced household can hide routine guidance without losing access to it.

## 2. Node and capability cards

Every node card shows its icon, plain-language name, enabled state and a small information control.
The information control must work with hover, keyboard focus and tap—not hover alone—and gives a
one- or two-sentence description. The node title is a link to `/settings/guides/{nodeKey}`.

The detail page includes:

- what the node is for and what deliberately belongs elsewhere;
- the common first tasks and a short “getting started” path;
- its main pages/features and which roles can use them;
- what it contributes to Hub, Calendar, Atlas Agenda, Search, Corners and Notifications;
- important privacy/sensitivity behaviour and what enabling/disabling changes;
- links to related nodes and examples of the single source of truth.

Each node page has a quiet **About [node]** link back to this information. A browser preference,
namespaced to the signed-in User, may hide contextual guide prompts once familiar; Manage
HomeStack can restore them. The permanent guide remains available through Manage HomeStack.
Hiding a guide never disables a feature or deletes data.

## 3. Version history inside the app

Add **What’s new / Version history** under Manage HomeStack. It shows the installed version first,
then reverse-chronological releases with date, a plain-language title, key changes, migration or
deployment notes where useful, and links to affected node guides.

`VERSION_HISTORY.md` remains the canonical authored history. Generate a small structured release
manifest from it at build/release time (or generate both from one structured source); do not keep a
second manually edited history that can drift. The UI must work offline and must not fetch GitHub.
The release script `scripts/generate_version_manifest.py` creates the checked-in offline manifest
and its `--check` mode detects drift. Optionally mark the latest version seen per User later so
**What’s new** can highlight unread releases.

## 4. Fewer visible nodes through capabilities

Avoid equating every bounded backend owner with a top-level navigation destination. A broad node
may expose optional **capabilities** which the household enables independently. Capability toggles:

- change navigation, tabs, forms, widgets and Search exposure, not table ownership;
- never delete existing records when switched off;
- show the effect before confirmation and restore the prior data when re-enabled;
- retain permission and privacy rules independently of whether the capability is visible;
- may be suggested during onboarding but remain editable under Manage HomeStack.

### Recommended consolidation

- **Homestead → Stock & storage** absorbs planned Inventory: pantry/fridge/freezer, cleaning and
  household consumables, pet food, storage locations, quantities, low-stock/expiry reminders and
  “send to Atlas shopping”. Hearth can query this capability later without owning stock.
- **Homestead → Assets & vehicles** absorbs the remaining planned Assets scope. Home appliances,
  warranties, rooms and maintenance already belong to Homestead (D21); the optional capability
  adds vehicles, tools, electronics, valuables, registration/service history and protected
  documents. Sensitive fields retain stronger access even though the UI sits inside Homestead.
- **Homestead → Household guide** is the recommended future home for the currently separate Home
  Wiki experience: emergency/reference pages, manuals and house-running instructions. It remains
  optional and can link to Pets or other owners without copying their structured data.
- **Homestead projects** should cover room renovations, repairs and home improvements. Travel owns
  trip planning, and Atlas lists cover lightweight general projects. Do not build a separate
  Projects node until a real non-home workflow needs boards, dependencies or project budgets.
- **Books** is a possible later consolidation candidate, but usage should decide its destination:
  study/course reading belongs in Education, while a simple household reading/wish list can use
  Atlas. Do not force an existing full household library into either merely to remove one label.

Keep **Solace**, **Fitness**, **Health**, **Education**, **Pets**, **Travel** and reward-bearing
**Meridian** as distinct owners because their privacy, history or workflows differ materially.
They may be grouped more compactly in navigation, but merging their data would weaken clear
ownership. Atlas remains the shared list/agenda surface rather than absorbing the Meridian reward
economy.

## 5. Delivery slices

1. **Shipped v0.34.0:** correct My Corner routing and accessible node-card descriptions/routes.
2. **Shipped v0.34.0:** guide content, disabled-node access and contextual prompt dismissal.
3. **Shipped v0.34.0:** generated offline version-history manifest and installed version display.
4. **Future:** add capability metadata/toggles, beginning with Homestead Household guide, then migrate the
   future Inventory/Assets specs before either is implemented as a separate node.

## 6. Acceptance

- Keyboard, mouse and touch users can learn what every available node does before enabling it.
- A node guide explains its first useful workflow and cross-node effects without exposing admin-
  only or sensitive details.
- The in-app installed version and release list match `VERSION_HISTORY.md` in CI.
- Hiding contextual guidance removes prompts only; the Manage guide remains discoverable.
- Disabling a capability hides its UI/widgets but preserves records and restores them on re-enable.
- A clean installation can use stock, vehicles/assets and household reference material inside
  Homestead without three additional top-level navigation items.
