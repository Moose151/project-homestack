# Document 9 — Node Model Decision Record

> Canonical. Supersedes earlier versions. Records *why* HomeStack uses the node set it does.
> Cross-cutting build/architecture decisions live in `00_README_and_Changelog.md` (D1–D18).

## 1. Decision

HomeStack uses a **small, deliberate set of confirmed nodes** rather than many small
overlapping ones.

**Confirmed opt-in nodes:** Atlas · Home Wiki · Pets · Education · Inventory · Assets ·
Hearth · Travel · Projects · Health · Meridian · Solace.

**Core platform services:** Hub · Calendar (`scheduling`) · People · Notifications · Search ·
Documents/Attachments · Permissions · Settings · Backups.

> The durable Event Bus listed as a core service in earlier drafts is **deferred** (D4):
> node interaction uses an internal signal interface, not a user-facing service or bus.

## 2. Reason

HomeStack is meant to be broad but not convoluted. Too many nodes produce confusing
navigation, duplicated data, overlapping responsibilities, harder permissions, more
maintenance, a poorer kiosk experience and a fragmented feel. A deliberate node set keeps the
system logical and keeps a solo developer able to finish it.

## 3. Consolidation decisions

- Vehicles, warranties, appliances, tools, home maintenance → **Assets**
- Subscriptions → **Solace**
- Documents → core **Documents/Attachments** service
- People → core service
- Garden → **Projects** or **Inventory** by context
- Library → parked unless it outgrows simple asset tracking
- Fitness → parked under Health/future
- Smart Home → future integration

## 4. Consequences

**Positive:** cleaner navigation, easier permissions, easier kiosk design, less duplication,
better long-term maintainability, more deliberate expansion.

**Trade-offs to manage:** some nodes are broad — Assets must handle several asset types
cleanly; Atlas must not sprawl into a project manager; Projects must not absorb everyday
lists. Clear boundaries are maintained in each node spec's "what does / does not belong"
sections.

## 5. Rule for future nodes

A new node is justified only when it: is a major household domain; has a unique workflow; needs
unique permissions; has its own data model; appears meaningfully on Hub/Calendar; cannot fit
cleanly inside an existing node; and would be independently useful to households. Otherwise it
is a feature inside an existing node.

## 6. Meridian & Solace position (D13, D14)

Meridian and Solace are confirmed **native nodes**, not external integrations. They already
exist as working apps in the household and are migrated in by rebuilding their shells on
HomeStack's shared services, reusing their proven business logic, and importing their live
data. No iframe/external-link layer is built. Meridian migrates early (no sensitive data);
Solace migrates after the security foundation is mature.

## 7. Final position

HomeStack grows through deliberate expansion, not accidental sprawl. The node model stays
stable unless a future feature clearly proves it needs its own domain.
