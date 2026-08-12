# Document 7 — UI/UX Design Guide

> **Canonical interface contract.** HomeStack should feel like one household product across Hub,
> nodes, mobile web and kiosk. Current product status belongs in `HANDOVER.md`; this guide defines
> stable experience rules.

## 1. Experience goals

HomeStack should feel:

- warm and household-oriented;
- calm rather than dense;
- modern but not ornamental;
- touch-friendly;
- understandable without knowing internal node names;
- consistent between domains;
- safe for shared/child surfaces;
- responsive from phone to desktop.

It should not feel like enterprise software, a database admin tool, or several unrelated apps
sharing one login.

**Experience consistency matters more than feature count.**

## 2. Responsive web is the primary everyday surface

Current priority is the responsive web/PWA experience used on phones and laptops. Kiosk remains a
first-class supported surface, but ordinary adult workflows must not be designed desktop-first and
then squeezed onto mobile.

- **Phone:** one-column flow, compact contextual navigation, bottom/app-style shell, large touch
  targets, progressive disclosure.
- **Tablet:** touch-first layout with room for side-by-side content where useful.
- **Desktop:** sidebar navigation, wider management/report layouts and denser comparison where
  genuinely helpful.
- **Kiosk:** large simple cards, minimal typing, avatar/PIN entry, clear session ownership and
  automatic timeout.

## 3. Navigation

Navigation uses household language first and internal node names second.

Examples of current destinations include:

- Home / Hub;
- Calendar;
- Lists & notes / Atlas;
- School & study / Education;
- Household guide / Home Wiki;
- Pets;
- Our home / Homestead;
- Tasks & rewards / Meridian;
- Money / Solace;
- Fitness & Training;
- Travel;
- My Corner / household member Corners;
- Manage HomeStack / People & access for administrative tasks.

A Person-scoped destination labelled **My** must resolve the signed-in User's linked Person first.
Alphabetical order is never identity. If no Person is linked, show an explicit setup/selection
state rather than another member's information.

Desktop groups destinations by purpose. Mobile keeps a small user-configurable shortcut set plus a
complete **More** directory. Hidden/disabled/unauthorized destinations are not shown, but backend
permissions remain authoritative.

The global shell owns app navigation. Hub is a daily information/action surface, not a second copy
of the sidebar.

## 4. Shared design system

Every domain uses shared components/tokens for:

- buttons/actions;
- cards/surfaces;
- forms/fields;
- modals/sheets/dialogs;
- tabs/section navigation;
- tables/list cards;
- badges/status;
- empty/loading/error states;
- notifications;
- avatars/People selectors;
- calendar/event presentation;
- confirmation/destructive actions.

A node may have an accent/identity but does not invent a separate visual language.

## 5. HomeStack brand

Brand source assets live in `brand/`; generated web assets live under
`frontend/public/brand/`. Use the shared `Logo` component rather than hand-cropping/resizing source
renders at each call site.

- **Mark:** compact house/stack icon for shell/favicon/app-icon contexts.
- **Wordmark:** name-only treatment where appropriate.
- **Lockup:** introductory/sign-in presentation, not repeated decorative branding on every page.

Any replacement should remain legible at small shell sizes and on both light/dark surfaces.

## 6. Colour and identity

People colours are useful for Calendar/household recognition. Nodes may have accent colours, but
status must never be communicated by colour alone.

Colour inputs use the shared labelled palette plus custom choice where needed. Calendar rows may
inherit Person/source colour when no explicit event colour is chosen.

Avoid maintaining separate colour pickers/palettes per node.

## 7. Mobile interaction rules

- Minimum touch target should normally be ~44px for primary/compact tap controls where practical.
- Routine editing must not require horizontal table scrolling.
- Dense desktop tables should become readable cards below the desktop breakpoint unless true
  column comparison is essential.
- Put the common fields/actions first; advanced recurrence/visibility/admin fields use progressive
  disclosure.
- Keep destructive actions separated and confirmed where recovery is difficult.
- Surface failed actions beside the workflow; do not rely on silent console errors.
- Preserve URL/deep-link state for tabs/detail records where notifications, Calendar, Search or
  Corners link into them.

## 8. Forms

Forms should ask for the minimum useful record first.

Use:

- explicit labels (not placeholder-only fields);
- saved entity selectors rather than duplicate free-text identity/institution/person data;
- inline validation with actionable messages;
- sensible defaults without silently assuming another household member;
- Cancel that does not submit;
- clear optional/advanced grouping;
- confirmation when a state transition has non-obvious downstream effects.

## 9. Calendar UX

Calendar is a shared timeline rather than a node-specific page.

- Month/week/day/agenda remain understandable on phone and desktop.
- Person/source colours have nearby labels/legend support.
- Node-owned events deep-link to the owning record; editing occurs at the source unless the event
  is Calendar-owned.
- Rotating schedules (D23) show the calculated state distinctly from normal event cards and visibly
  mark exceptions.
- Month browsing should preserve context: selecting a day can open detail/sheet without unexpectedly
  replacing the entire month view.

## 10. Hub UX

Hub answers "what needs attention today?" rather than "what features exist?".

Widgets should be:

- permission-aware;
- glanceable;
- action-oriented where appropriate;
- calm in empty/normal states;
- sized/orderable without turning into a dashboard-design tool;
- safe for the surface (web vs kiosk).

Do not expose sensitive counts/titles/amounts merely because a widget itself is visible.

## 11. Corners / People-centred UX

Corners aggregate permitted information about a Person without taking ownership from source nodes.

- My Corner defaults to the current User's linked Person.
- Activity links open the exact owning record where permitted.
- Expanded detail re-checks permission before display.
- Suggestions/reactions should feel household-friendly without becoming a noisy social network.

## 12. Node-specific direction

**Atlas:** fastest path to ordinary household notes/lists; Grocery deliberately simple; Shopping
supports richer product/link context.

**Meridian:** playful/kid-friendly where the child interacts; efficient adult cockpit for setup,
approvals and monitoring.

**Education:** deadline/timetable clarity; Study defaults to the current linked Person.

**Pets:** visual pet identity plus quick treatment/appointment action.

**Homestead:** warm spatial/property organisation; rooms/floor plan/plans should feel connected to
the home rather than an asset register.

**Solace/Money:** sensitive, clear and calm; prioritize "what needs doing / what is safe" over dense
finance jargon.

**Fitness & Training:** large live-workout controls, previous-performance context, fast set editing
and readable history; do not visually imply medical Health.

**Travel:** project-like trip page, progressive booking sections, clear booked/planned state,
Things-to-do grouped by day plus unscheduled options.

**Home Assistant (future):** status first, safe controls second, explicit stale/offline state.

**Hearth (future):** recipe/meal enjoyment and direct handoff to Atlas Grocery rather than a
separate shopping experience.

## 13. Kiosk UX and security

Typical state:

```text
ambient -> avatar -> PIN -> personal dashboard -> permitted workflow -> timeout
```

Kiosk defaults to large, simple, low-typing interactions. Child-accessible content can include
Tasks & rewards, Education, Pets, Calendar and simple Atlas/Grocery household actions as permitted.

Sensitive by default: Money, medical Health, protected documents, administrative settings and
other finance/private records.

Kiosk UI hiding is not security; backend permissions and sensitive re-auth remain authoritative.

## 14. PWA / notification UX

Web Push should be useful rather than noisy:

- ask for notification permission in context, not immediately on first page load;
- explain why notifications are useful before the browser permission prompt;
- preferences are per User and can vary by category/device;
- quiet hours and lead times are understandable household settings;
- lock-screen text is deliberately sparse for sensitive/private items;
- tapping a notification opens the exact relevant HomeStack destination and then re-checks access;
- an unavailable/expired subscription degrades without making the rest of Notifications unusable.

Canonical delivery/security detail: `32_Core_Notifications_and_Push.md`.

## 15. Feedback and delight

Use small feedback moments where they support household motivation (task completion, assignment
completion, workout finish, etc.) but avoid turning every action into a celebration.

Feedback should clearly answer:

- Did the action work?
- What changed?
- Is anything else required?

## 16. Accessibility

Required baseline:

- keyboard navigation for web/admin flows;
- semantic labels/accessible names;
- screen-reader-compatible controls;
- visible focus states;
- sufficient contrast in light/dark mode;
- status not encoded by colour alone;
- large touch targets;
- text/layout that survives reasonable browser zoom/font scaling.

## 17. Pre-release UX checklist

Before shipping a screen/workflow, verify:

- Does it feel like HomeStack rather than a one-off app?
- Is the phone experience intentional rather than merely responsive CSS?
- Are common actions obvious and fast?
- Are advanced/admin options progressively disclosed?
- Do loading/empty/error states exist?
- Do dark mode and keyboard/touch interactions work?
- Is current-Person identity correct?
- Are disabled/unauthorized actions/destinations represented clearly?
- Can sensitive information leak through summaries, widgets, activity, Search, Calendar or
  notifications?
- Does a deep link return the user to a stable, meaningful location?

The old partner-pilot checklist is historical acceptance evidence now that two-account/real-device
acceptance has been completed; new UX findings should be handled as ordinary bugs/feature work,
not by re-running that historical gate.