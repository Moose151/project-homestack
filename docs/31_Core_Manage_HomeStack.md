# Core Spec — Manage HomeStack and In-app Guides

> **Status:** the management/guidance surface is shipped. Node summaries/guides for enabled and
> disabled nodes, dismissible contextual guidance and generated offline Version history are live.
> The capability-consolidation model described below is still a **future proposal** and must not be
> presented as available functionality.

## 1. Purpose

Manage HomeStack should answer:

- **What can HomeStack do?**
- **What has this household enabled?**
- **What changed in this version?**
- **Where do I configure household-wide HomeStack behavior?**

It is a core management surface, not a node and not a replacement for technical server operations.

## 2. Node guides — shipped

Every available node can expose a plain-language guide covering:

- what the node is for;
- what deliberately belongs elsewhere;
- common first tasks/getting-started workflow;
- major screens/features;
- role/privacy/sensitivity behavior;
- Hub/Calendar/Search/Corners/Notifications interactions where relevant;
- what enabling/disabling changes;
- links to related domains and their source-of-truth boundaries.

Guides remain accessible for disabled nodes so a household can understand a capability before
enabling it.

Contextual **About [node]** links/prompts may be dismissed per signed-in User. Dismissing guidance
never disables the node or deletes data; the permanent guide remains available in Manage HomeStack.

Books is a current node and should have/retain a guide like the other shipped domains. Its guide
should describe personal reading shelves, ratings and shared Book Clubs rather than treating it as
an Atlas/Education subfeature.

## 3. Version history — shipped

Manage HomeStack includes an offline **What’s new / Version history** surface.

`VERSION_HISTORY.md` remains the authored historical source. The release-manifest generation/check
flow prevents the frontend copy from silently drifting from it.

The interface should show the installed version, reverse-chronological release information and
useful deployment/migration notes without needing GitHub/network access.

Future optional polish: per-User latest-seen version/unread-release indicator.

## 4. Node enablement and configuration

Node cards communicate enabled/disabled state and use accessible information controls (mouse,
keyboard and touch, not hover-only).

Disabling a current node should hide normal navigation/contributions according to the node system
without deleting its data. Re-enabling restores access subject to permissions.

The node registry remains the authoritative current catalogue. Documentation must not omit a real
seeded node or invent a future one based only on an old planning spec.

## 5. Future capability model — proposal only

A broad domain may eventually expose independently enabled **capabilities** so navigation can stay
compact without merging databases blindly.

If implemented, a capability toggle should:

- alter navigation/tabs/forms/Hub/Search exposure;
- preserve data while hidden;
- preserve underlying permissions/privacy;
- clearly explain the effect before disabling;
- restore prior state/data presentation when re-enabled;
- separate presentation grouping from data ownership/migration.

No capability framework should be treated as shipped until models/config/API/UI and data migration
behavior actually exist.

## 6. Proposed Homestead capabilities

### Stock & storage

Potential future presentation/ownership boundary for the planned Inventory scope:

- pantry/fridge/freezer;
- household consumables and pet food;
- storage locations/boxes;
- quantity/low-stock/expiry;
- suggestions into Atlas Grocery/Shopping.

Hearth could query stock later but still sends the actual shopping requirement to Atlas Grocery.

### Assets & vehicles

Potential future Homestead capability for non-home assets/vehicles:

- vehicles;
- tools/electronics/valuables;
- registration/service/insurance context;
- protected identifiers/documents.

Home appliances/warranties/rooms/home maintenance already belong to Homestead (D21) and must not be
duplicated into a second Assets store.

### Household guide

Potential future presentation of the current Home Wiki experience inside Homestead to reduce
navigation. If implemented, it must preserve Home Wiki pages/categories/permissions/Search/stable
links and avoid data loss.

Until then, **Home Wiki remains a current independent node**.

## 7. Projects boundary

Homestead owns home improvements/room projects; Travel owns trip planning; Atlas owns lightweight
general lists.

A top-level Projects node remains evidence-gated. Do not create it merely to provide a menu entry
for work already represented by existing domains.

## 8. Books boundary

Books is **not a current consolidation target**.

The shipped Books domain has persistent personal reading state plus shared club workflows:

- Want to Read / Reading / Read shelves;
- one User rating/notes record per Book;
- Book Clubs and membership;
- club shelf state and ordered up-next queue.

Education may later reference a Book for course reading and Atlas may contain a shopping wish for a
physical book, but neither is a clean owner for Books' existing reading/club model.

Only revisit navigation/ownership if real household use later demonstrates a simpler destination
that preserves all existing data/permissions/links. Do not consolidate Books solely to reduce one
navigation label.

## 9. Domains that should remain distinct

Keep the following separate unless a new explicit product decision replaces their current privacy/
workflow boundaries:

- Solace / Money;
- Fitness & Training;
- future medical Health;
- Education;
- Pets;
- Books;
- Travel;
- reward-bearing Meridian.

Grouping navigation more compactly is different from merging ownership.

## 10. Current delivery status

Shipped:

1. correct Person-aware navigation/guide entry points;
2. accessible node-card summaries and detailed guides;
3. guides for disabled nodes;
4. dismissible contextual guidance with permanent recovery in Manage HomeStack;
5. generated offline Version history and installed-version display.

Future only:

6. capability metadata/configuration framework;
7. Homestead Household guide/Stock & storage/Assets & vehicles capability toggles;
8. any data-preserving migration/presentation work needed to implement those proposals.

## 11. Acceptance — current shipped surface

- Keyboard, mouse and touch Users can inspect what available nodes do before enabling them.
- Enabled and disabled node guides remain discoverable as intended.
- Guides explain source ownership/security without exposing protected record detail.
- Dismissing contextual guidance hides guidance only.
- Installed version/release history stays synchronized with `VERSION_HISTORY.md` through the
  generation/check workflow.
- Node enable/disable behavior preserves its underlying data according to the existing node system.

## 12. Acceptance — future capability framework

Only when capability consolidation is actually implemented should these become release criteria:

- hiding a capability removes its navigation/widgets/Search presentation without deleting records;
- re-enabling restores the prior data/presentation;
- capability permissions remain enforced while hidden;
- migration from a formerly separate owner is explicit, data-preserving and tested;
- a clean installation can intentionally choose the proposed Stock & storage / Assets & vehicles /
  Household guide presentation without those being falsely advertised beforehand.

Until that implementation exists, these criteria describe the proposal rather than current
HomeStack behavior.