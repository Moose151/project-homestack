# Document 3 — UI/UX Design Guide

> Canonical. Supersedes all earlier UI/UX docs. Decisions D1–D23 in `00_README_and_Changelog.md`.

## 1. Purpose

Defines HomeStack's interface and experience standards. HomeStack must feel like **one
family-oriented platform**, not a set of separate apps.

## 2. Design philosophy

Should feel: warm, friendly, calm, modern, touch-friendly, family-oriented, kiosk-ready.
Should not feel: corporate, dense, technical, enterprise-like.

Guiding rule: **experience consistency matters more than feature count.**

Colour entry uses the shared HomeStack palette: a broad set of named-by-position visual swatches
with pressed state and keyboard labels, plus the native custom picker for unrestricted colours.
Calendar events may clear an explicit colour to inherit their Person/whole-family colour. Do not
replace a palette with an unlabelled tiny colour well or maintain different palettes per node.

## 3. Navigation model

Any person-scoped destination labelled as the user's own—such as **My Corner** or **Study**—first
resolves the signed-in User's linked Person. Alphabetic order is never an identity default. A
visible person switcher may then move to another permitted member; an unlinked User gets an
explicit selection/setup state rather than somebody else's data by default.

Navigation leads with the household task in plain language; the node name is supporting context,
not required vocabulary. Current shipped examples are: Home (Hub) · Calendar · Lists & notes
(Atlas) · School & study (Education) · Books · Household guide (Home Wiki) · Pets · Our home
(Homestead) · Tasks & rewards (Meridian) · Money (Solace). Future nodes follow the same rule.

Desktop groups permission-aware destinations by purpose: Start here, Plan & organise, Household
and Money. Mobile keeps four user-configurable shortcuts plus More; More is always a complete,
descriptive directory of every available destination, not merely an overflow list. Admin routes
use task labels such as People & access and Manage HomeStack. Hidden or disabled nodes never
appear.

Documents are not a separate nav item — they live in the shared Documents/Attachments service
surfaced inside each node. Children get a simplified navigation (§4).

## 4. Child / kiosk primary navigation

Children primarily see: Tasks (Meridian) · Education · Pets · Meals (Hearth) · Calendar ·
simple Atlas lists.

Children do **not** see by default: Solace · Health · Assets · sensitive Documents · Settings
· admin pages.

## 5. Shared design system

Every node uses shared components — buttons, cards, forms, modals, tables, lists, widgets,
notifications, avatars, PIN pad, calendar cards, empty states, error states, kiosk cards. No
node creates its own visual style. This is enforced in code review (Coding Standards §"node
checklist").

## 6. Colour & identity

Each person has a colour used across Calendar and Hub. Each node may have an icon/accent
colour, but the global HomeStack design language stays consistent. Suggested node accents:
Atlas blue · Home Wiki warm neutral · Pets green · Education purple · Inventory teal · Assets
slate · Hearth orange/red · Travel sky blue · Projects amber · Health red/pink · Meridian gold
· Solace teal/green · Homestead warm terracotta · Home Assistant blue · Fitness coral/red.

### 6a. The logo (added 2026-08-10)

Three marks, each with one job. Sources in `brand/`, web assets in `frontend/public/brand/`
(rebuilt by `scripts/build_brand_assets.py`), and every use goes through
`components/Logo.tsx` so sizes and alt text are decided once.

- **Mark** (the house with the stack) — the sidebar header, the kiosk ambient screen, the
  favicon and the app icons. Used wherever space is tight or the word "HomeStack" is already
  written beside it, in which case the image is `aria-hidden` rather than repeating the name.
- **Wordmark** — a wide strip where the name must carry itself. Light-toned, so it belongs on
  dark surfaces first.
- **Lockup** (mark above the name) — **one per surface**, on the screen that introduces the app:
  the web sign-in page. Not a page decoration.

Check any replacement against both the paper and the dark surface, and at 36px as well as full
size — the sidebar draws it small, and a mark that dissolves there is the wrong mark.

## 7. Layouts

- **Mobile:** single column, bottom navigation, large tap targets, fast actions.
- **Tablet:** two-column, touch-first.
- **Desktop:** sidebar navigation, widget grid, more detail.
- **Kiosk:** large cards, minimal typing, avatar login, automatic timeout, ambient mode.

The global shell owns destination navigation. Hub should not repeat the same navigation as a
second launchpad; it should prioritise useful household widgets, summaries and next actions.
Shared page headings show one clear title and supporting sentence, and shared tabs use a compact
section picker on phones and a segmented control where space allows.

Dense management tables are desktop tools, not mobile layouts. Below the large desktop
breakpoint, management records must become readable cards with the same information and actions;
horizontal scrolling is reserved for genuinely tabular comparison, not routine editing. Forms
ask for the common minimum first and place less-used scheduling, visibility or rule fields in a
clearly labelled progressive section. The mobile shell already identifies the current
destination, so a page may omit a second large title when doing so materially improves the
first-screen workspace.

## 8. Kiosk UX

States: ambient → avatar selection → PIN entry → personal dashboard → node kiosk view →
timeout return.

Kiosk-safe widgets: date/time, weather (future), calendar, meals, pet reminders, homework,
birthdays, travel countdowns, simple tasks.

Not kiosk-safe by default: bills, health, sensitive documents, financial events, admin
settings. Opening a sensitive node on kiosk requires re-auth and a shortened timeout
(Security doc §6–7).

## 9. Node UI expectations (brief)

Atlas: fast lists/checklists/groceries/notes. Home Wiki: readable reference + emergency info.
Pets: pet cards, photos, treatment reminders. Education: homework cards, deadlines, events.
Inventory: low-stock cards, expiry alerts. Assets: asset cards, maintenance reminders,
documents. Hearth: meal cards, recipes, dinner tonight. Travel: trip cards, countdowns,
itinerary, packing. Projects: project cards, milestones, task boards. Health: secure, private,
minimal exposure. Meridian: kid-friendly reward/task cards with celebrations. Solace:
restricted, clear finance dashboard. Homestead: warm home/room cards and obvious source links.
Home Assistant: calm grouped status first, safe controls second, and unmistakable stale/offline
state; one-column touch-friendly cards on phones.

## 10. Positive experience

Small moments of delight: "✓ Great job!" on task complete, "⭐ Assignment complete!" on
homework, gentle confirmations on pet/medication logging. Future: achievements, badges,
streaks, celebrations (Meridian). Children should enjoy using HomeStack.

## 11. Accessibility

Support: dark mode, large text, high contrast, colour-blind-safe status indicators, keyboard
navigation, screen readers, large touch targets. Status is never conveyed by colour alone.

### 11.1 Rotating Calendar schedules (D23)

Setup explains the anchor date in plain language and shows a tappable preview of every day in
the cycle; the common 2/2/3/2/2/3 shared-care pattern may be pre-filled, but labels, People,
colours and every state remain editable. Month view uses a continuous two-colour strip along
the top of each otherwise-neutral day cell, with a nearby labelled legend; moving between months
recalculates every visible strip.
Week, day and agenda views may use labelled status badges. An exception carries a visible swap
marker, so status is not conveyed by colour alone. Phones retain a compact seven-column month
overview for the rotation. The complete six-week grid is the primary phone Month surface and may
run edge-to-edge to preserve useful cell width. A day may show one compact coloured event label
and a count rather than expanding into an agenda. Tapping a date opens that day's rotations and
events in a bottom sheet; entering full Day view remains a separate explicit action, so the Month
layout does not change while browsing. Horizontal swipe may move between months, but arrow and
Today controls remain present and keyboard-accessible. Event labels may use person/source colours,
while the care strip remains separate and labelled nearby. Setup/exception editing uses the
shared bottom sheet with at least 44px action targets. Changing one date must say explicitly that
other dates are unaffected and must offer “restore repeating plan”.

## 12. Pre-release UX checklist

Before shipping a screen, confirm: does it feel like HomeStack? Is it touch-friendly? Usable
on mobile? Safe on kiosk? Dark-mode supported? Are permissions reflected clearly (and is
nothing sensitive leaking into a child/kiosk view)? Is it simple enough for its target users?

### 12.1 Household account and navigation consistency

- Navigation discovery is permission-aware as well as node-enable-aware. Do not show a
  destination, quick action, search destination or contributed Hub widget that the current user
  cannot open.
- Apply the same rule within a destination: hide protected tabs, actions and cross-node links when
  the current account cannot use the owning node, while keeping the backend permission check as
  the authority. Do not lead a user into a predictable access-denied dead end.
- A trusted adult partner normally uses the **manager** role. Sensitive Money access is a separate,
  explicit account choice and must not require promoting that person to administrator.
- The mobile shell already names the active destination. Page headers are normally desktop-only on
  first-level screens; keep them on mobile only when they carry unique context or an action that is
  not available elsewhere.
- Management lists use readable cards below the desktop breakpoint when each row contains actions
  and descriptive content. Retain a desktop table for efficient comparison; reserve horizontal
  scrolling on phones for genuinely tabular reports.
- Label form controls explicitly, surface failed actions beside the workflow, give touch actions
  at least a 40–44px target and confirm removal when the effect is destructive or difficult to
  reconstruct.
- Use `docs/PARTNER_PILOT_READINESS.md` as the release gate for visible nodes and single-entry
  cross-node workflows.
