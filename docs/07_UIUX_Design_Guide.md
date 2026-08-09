# Document 3 — UI/UX Design Guide

> Canonical. Supersedes all earlier UI/UX docs. Decisions D1–D23 in `00_README_and_Changelog.md`.

## 1. Purpose

Defines HomeStack's interface and experience standards. HomeStack must feel like **one
family-oriented platform**, not a set of separate apps.

## 2. Design philosophy

Should feel: warm, friendly, calm, modern, touch-friendly, family-oriented, kiosk-ready.
Should not feel: corporate, dense, technical, enterprise-like.

Guiding rule: **experience consistency matters more than feature count.**

## 3. Navigation model

Core navigation (permission-aware; hidden/disabled nodes never appear):
Hub · Calendar · Atlas · Home Wiki · Pets · Education · Inventory · Assets · Hearth · Travel ·
Projects · Health · Meridian · Solace · Homestead · Home Assistant · Settings.

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
· Solace teal/green · Homestead warm terracotta · Home Assistant blue.

## 7. Layouts

- **Mobile:** single column, bottom navigation, large tap targets, fast actions.
- **Tablet:** two-column, touch-first.
- **Desktop:** sidebar navigation, widget grid, more detail.
- **Kiosk:** large cards, minimal typing, avatar login, automatic timeout, ambient mode.

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
overview for the rotation, with large enough day targets leading to the detailed day view;
setup/exception editing uses the shared bottom sheet with at least 44px action targets. Changing
one date must say explicitly that other dates are unaffected and must offer “restore repeating
plan”.

## 12. Pre-release UX checklist

Before shipping a screen, confirm: does it feel like HomeStack? Is it touch-friendly? Usable
on mobile? Safe on kiosk? Dark-mode supported? Are permissions reflected clearly (and is
nothing sensitive leaking into a child/kiosk view)? Is it simple enough for its target users?
