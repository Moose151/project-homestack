# Document 10 — Future Features & Parking Lot

> Canonical. Supersedes earlier versions. Holds future ideas without licensing node sprawl or
> premature scope. Decisions D1–D18 in `00_README_and_Changelog.md`.

## 1. Parking-lot rule

A future idea usually becomes a **feature inside an existing node**, not a new node. New nodes
require strong justification (Node Decision Record §5).

## 2. Deferred-but-anticipated infrastructure

These are intentionally not in V1 but the architecture leaves room for them:

- **Durable event bus** (D4) — the internal `events` signal interface can be re-pointed at a
  real broker later without changing callers.
- **Redis + Celery + Celery-beat** (D5) — added when reminders/background work outgrow the
  scheduled management command.
- **Attachment per-row ACL** (`attachment_permissions`) (D11) — if `visibility`/`sensitivity`
  proves too coarse.
- **Wiki page version history** (`wiki_page_versions`) — schema anticipated, not built in V1.
- **Token auth / 2FA / passkeys / biometrics** — added with native apps and any remote access.

## 3. Parked under existing nodes

**Atlas:** rich text/Markdown, templates, recurring lists, quick capture, voice input, smart
grocery suggestions.
**Home Wiki:** page templates, version history, linked pages, emergency mode, house-sitter
mode, procedure blocks.
**Pets:** feeding schedules, food-inventory link, weight graphs, pet insurance, house-sitter
pet mode, Meridian pet tasks.
**Education:** study timers, reading logs, grades, term imports, university dashboard,
Meridian homework tasks.
**Inventory:** barcode scanning, QR storage labels, expiry dashboard, smart grocery
suggestions, storage-box tracking.
**Assets:** odometer reminders, warranty claims, service costs, QR labels, maintenance
templates, insurance tracking.
**Hearth:** recipe import, meal voting, nutrition, leftovers, batch cooking, pantry checks,
grocery generation.
**Travel:** maps, weather, currency conversion, travel journal, pet-care automation, Solace
travel budgets.
**Projects:** Kanban boards, templates, budget links, photo progress, garden templates, large-
purchase workflow.
**Health:** prescription tracking, health graphs, provider directory, emergency health card,
encrypted health attachments, field-level encryption.
**Meridian:** achievements, streaks, household challenges, task templates, weekly summaries.
**Solace:** subscriptions (richer), travel/grocery/asset-purchase budget integration, reports,
exports, encrypted finance fields.

## 4. Future platform features

PWA · native Android/iOS · desktop app · offline mode · push/email notifications · external
calendar sync · plugin architecture · webhooks · advanced automation · AI-assisted search ·
OCR · semantic search.

**Node graph / "web" view (Obsidian-style)** — a visual map of the Hub at the centre with every
node hanging off it, coloured lines connecting nodes to show how they interact and what data
flows between them (which signals/events each sends and receives — see each node spec's "Events"
section + D4). Clicking a node's icon navigates to that node's page. *Not important — a fun,
exploratory visualisation, not core functionality.* Naturally driven by the existing decoupled
events interface (D4): the edges are the publish/consume relationships already declared per node.
Parked until the core product is solid; revisit as a delight feature (possibly alongside the Hub
work, but well after V1).

> Per D3, the mobile/desktop tech choice (React Native vs. Tauri vs. PWA) is deliberately
> undecided; a PWA is the likely first phone bridge.

## 5. Not for V1

Native mobile/desktop apps · full offline mode · Health node · native Solace migration (comes
after security maturation, not in the first usable V1) · OCR · AI · plugin system · public
internet exposure · external calendar sync · barcode scanning · field-level encryption.

> Multi-household and SaaS are **not parked for later — they are out of scope** (D1, D2).
> If HomeStack is ever released, it ships self-hosted (one household per install). The tenant
> column is carried only as cheap insurance, not as a roadmap item.

## 6. Future node review rule

Before creating a new node, ask: major household domain? unique workflows? unique permissions?
would it overload an existing node? would many households use it independently? If not, keep
it inside an existing node.
