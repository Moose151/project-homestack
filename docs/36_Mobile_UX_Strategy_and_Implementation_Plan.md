# Document 36 — Mobile UX Strategy and Implementation Plan

**Status:** canonical implementation strategy for the mobile-first HomeStack experience.

**Created:** 2026-08-13

**Relationship to other documents:** this document is an implementation companion to
`07_UIUX_Design_Guide.md`. Document 7 remains the stable interface contract; this document turns its
mobile-first principles into a concrete redesign and engineering sequence for the current shipped
application. Domain behaviour remains owned by the relevant node/core specification.

---

## 1. Executive recommendation

HomeStack needs a substantial mobile UX overhaul, but it does **not** need a frontend rewrite.

Keep:

- React and the existing routing/API architecture;
- Tailwind and the shared semantic design tokens;
- the warm HomeStack visual identity;
- the existing PWA/service-worker foundation;
- shared Button, Field, Card, Modal, Tabs and other reusable components where they remain suitable;
- existing backend permissions, sensitive re-authentication and deep-link behaviour.

Change the mobile information architecture.

The primary problem is not colour, spacing or rounded corners. The app has increasingly large
feature pages which work by adapting desktop-oriented layouts to narrower widths. Many screens now
technically fit a phone while still behaving like a desktop application: large pages, many tabs,
nested tabs, inline create forms, inline edit forms and expanded detail panels all compete for the
same small viewport.

The mobile programme should therefore be treated as **HomeStack Mobile UX v1**, with this goal:

> Make the phone the best way to use HomeStack, not merely a screen size HomeStack supports.

A mobile user should be able to open HomeStack with one hand, understand what needs attention,
reach any common destination quickly, add something from anywhere, complete ordinary actions
without fighting tabs or long forms, and encounter complex management UI only when deliberately
seeking it.

The core structural change is:

```text
CURRENT

Node
 └── enormous page
      ├── tab
      ├── tab
      ├── tab
      ├── nested tab
      ├── inline create form
      ├── inline detail
      └── inline edit form

TARGET MOBILE

Node home
 ├── important status
 ├── primary actions
 └── destinations
      │
      ├── list screen
      │    └── detail screen
      │         └── edit/create sheet or focused form screen
      │
      └── another list screen
```

Desktop and mobile should share data, routes, permissions and components, but they do **not** need
to use exactly the same composition. Responsive design is allowed to give the phone a genuinely
mobile information hierarchy.

---

## 2. Why the current phone experience feels unpolished

### 2.1 The shell is mobile-aware but most content pages are still desktop-shaped

`AppShell` already provides useful mobile foundations:

- a bottom navigation bar;
- configurable primary destinations;
- a complete More directory;
- global Search;
- Quick Create;
- notification access;
- safe-area padding.

However, the content system still relies heavily on each page independently deciding how its large
desktop layout should collapse. A single wide content container is shared globally, but mobile
quality is largely determined page by page. As functionality has accumulated, consistency has
drifted.

### 2.2 Long tab sets are being hidden rather than redesigned

The shared `Tabs` component sensibly turns a primary tab set with more than three items into a
mobile select control. That prevents overflow, but it can hide a deeper navigation problem.

For example, a phone user should not have to understand a nine-option selector containing concepts
such as Overview, Rooms, Maintenance, Appliances, Pool, Power & Water, Improvements, Contacts and
Finances simply to move around their home information. Those are mobile destinations, not merely
tabs.

A `<select>` is appropriate for choosing a value. It should not become the default answer to every
large section hierarchy.

### 2.3 Too much work happens inline

Many nodes create, edit and expand records in the same card/list/page that the user is browsing.
This is efficient on a large screen, but on a phone it creates long, unstable pages where the user
can lose context and where important actions move far away from the item being changed.

Routine mobile patterns should instead favour:

- index/list screen;
- record detail screen;
- focused create/edit sheet or screen;
- browser/PWA Back to return to the previous context.

### 2.4 Readability is sometimes sacrificed for density

The shared controls already meet a good touch baseline: fields are approximately 44px high, coarse
pointer controls receive a 44px minimum, and phone form controls are forced to 16px to avoid iOS
focus zoom. These are strengths that should remain.

The higher-level screens still use a large amount of 10–11px supporting text. Small microcopy is
fine for genuinely secondary labels, but meaningful instructions, status and metadata should more
often sit around 13–16px on phones.

### 2.5 Some experiences explicitly require horizontal panning

The clearest example is Homestead's interactive floor plan. The SVG currently uses a minimum width
of roughly 680px for the inside view and 760px for the whole-property view inside an overflowable
container. Panning is reasonable inside a deliberately opened spatial viewer; it should not be the
primary everyday way to navigate rooms on a phone.

### 2.6 Complexity indicators

The current page implementations are feature-rich. Source size is not itself a defect, but it is a
useful indicator of how much behaviour is being coordinated in single route-level components.
Current examples include approximately:

- Calendar: 64 KB;
- Atlas: 52 KB;
- Education: 68 KB;
- Homestead: 109 KB.

The redesign should progressively decompose both the UX and the implementation around stable mobile
subscreens rather than continue adding responsive conditions to monolithic page components.

---

## 3. Target mobile look and feel

The redesign should still look unmistakably like HomeStack.

Preserve:

- warm neutral backgrounds;
- soft cards and restrained shadows;
- teal primary action colour;
- node accent colours as identity/context rather than decoration;
- rounded surfaces;
- household-friendly language;
- light and dark semantic tokens;
- calm empty/normal states.

The target should feel closer to a polished native household application than a responsive admin
dashboard.

### 3.1 Typical phone screen

A normal phone screen should usually contain:

1. a compact app bar with only relevant global/contextual controls;
2. a clear title or immediate context;
3. at most a short summary/status block;
4. vertically flowing rows/cards containing the task at hand;
5. one obvious primary action where appropriate;
6. secondary/detail/configuration one level deeper.

### 3.2 Typography

Recommended practical baseline:

- important screen heading: about 20–24px;
- section/card heading: about 15–18px depending hierarchy;
- normal body/value/action text: 15–16px;
- supporting metadata: 13–14px;
- 10–11px reserved for true micro-labels, badges or low-priority annotations.

Do not solve dense screens by shrinking type.

### 3.3 Touch and reachability

- Keep approximately 44px minimum touch targets.
- Prefer full-row tap targets instead of tiny text links.
- Keep destructive actions away from primary actions and confirm irreversible operations.
- Place frequent mobile actions within natural thumb reach.
- Account for device safe areas and the on-screen keyboard.
- Avoid primary actions being covered by the fixed bottom navigation.

### 3.4 Progressive disclosure

The default flow should ask for the minimum useful record first. Advanced recurrence, visibility,
linkage and administrative options should be collapsed or moved to an advanced section where that
does not hide necessary information.

---

## 4. Mobile shell and global navigation

The shell should be redesigned before individual nodes so all later work has one stable mobile
frame.

### 4.1 Simplify the top bar

The current mobile top bar carries destination identity plus Search, Quick Create and Notifications.
That is too much global chrome competing inside a short phone header.

Recommended mobile app bar:

```text
┌──────────────────────────────────┐
│ ‹  Money                   🔔  ⋮ │
└──────────────────────────────────┘
```

Use:

- Back when the user is inside a detail/subscreen;
- current screen/destination title;
- notification access;
- one overflow/context menu when useful.

Search should remain globally available through More and be prominent on Home. A keyboard shortcut
can remain for desktop.

### 4.2 Elevate Quick Create into the bottom navigation

Quick Create already provides one of the best cross-domain capabilities in the app: reminders,
notes, calendar events, home plans/maintenance, books, points tasks and bills can be started from one
place.

It should become a first-class mobile action.

Recommended bottom bar:

```text
┌──────────────────────────────────┐
│ Home   Shortcut   ＋   Shortcut  More │
└──────────────────────────────────┘
```

Rules:

- **Home** fixed;
- **Add (+)** fixed in the centre;
- **More** fixed;
- two user-configurable destination shortcuts;
- Calendar should be a default shortcut for most users;
- the current permission/node-visibility filtering remains authoritative.

This gives the phone a stable mental model: go home, go somewhere common, add something, or find
everything else.

### 4.3 More becomes the mobile directory

More should contain:

- all enabled/authorized destinations grouped by purpose;
- Search;
- profile/account entry;
- appearance/preferences;
- administrative destinations for authorized users;
- shortcut customization.

Avoid duplicating a second dense dashboard inside More.

---

## 5. Shared mobile primitives to build first

Do not let each node invent its own mobile screen patterns. Add a small shared mobile layer above the
existing basic components.

Recommended primitives/concepts include:

- `MobileScreenHeader` — title, Back, optional contextual actions;
- `MobileSection` — consistent section spacing/heading;
- `MobileListRow` — large whole-row navigation/action target with leading icon/avatar, primary text,
  secondary metadata, trailing value/status/chevron;
- `MobileSettingsRow` — label, description/value and switch/chevron;
- `MobileSummaryCard` — compact status/attention overview;
- `StickyActionBar` — safe-area-aware bottom actions above app navigation;
- `MobileActionMenu` — contextual secondary actions;
- full-height/focused mobile form sheet using the existing Modal foundation;
- standard index → detail → edit/create routing pattern;
- standard mobile filter/sort sheet;
- standard saved/success feedback.

`Button`, `Field`, `Card`, `Modal`, `Badge`, `Avatar`, `AssigneeSelect` and semantic colour tokens
should generally remain underneath these patterns.

### 5.1 PageHeader changes

Phone actions should not rely on horizontally scrolling action rows. If a page has more than one or
two contextual actions, move them to the overflow menu or a dedicated action sheet.

### 5.2 Tabs changes

Keep tabs where there are two or three genuine peer views. For larger product hierarchies, use
subroutes/list rows instead of automatically converting everything to a select.

Secondary segmented controls can remain for small local choices such as:

- Personal / Book Club;
- Floor plan / Room list;
- All / Favourites / Emergency;
- day-specific filters.

---

## 6. Page-by-page redesign

## 6.1 Home / Hub

**Current direction:** relatively good. The Hub already collapses to one column on mobile.

**Target:** make the phone Hub a daily feed rather than a configurable dashboard first.

Opening viewport priority:

1. greeting/context if useful;
2. urgent/overdue items;
3. today/upcoming;
4. two or three high-value quick actions or user-selected widgets;
5. lower-priority widgets below.

Desktop can remain more dashboard-like. Mobile customization should remain possible but should not
turn the normal experience into dashboard administration.

## 6.2 Calendar

Calendar already has substantial mobile-specific work: a phone month grid, swipe navigation,
mobile view picker, floating Add action and selected-day bottom sheet. Refine this rather than
replace it.

### Mobile direction

- **Agenda** should be the default everyday reading mode on phone.
- **Day** should be the next most important view.
- **Month** should provide orientation, not attempt to display full event content in every cell.
- **Week** should become a horizontal day selector + readable agenda rather than a squeezed desktop
  seven-column calendar.

Example week pattern:

```text
Mon 10   Tue 11   WED 12   Thu 13   Fri 14
                    ●

Wednesday 12 August

08:30  School drop-off
10:00  Dentist
       With Dad tonight
15:30  Soccer training
```

Month cells should primarily show date, simple source/person indicators, event count and rotation
state. Tapping a date opens the existing-style day sheet with readable event rows.

Event create/edit should become a near/full-height phone sheet with sticky Save. Preserve the
current progressive `More options` approach and source-owned-event deep links.

## 6.3 Lists & notes / Atlas

Atlas contains some of the best existing mobile interaction patterns and should be a reference for
other nodes:

- whole-row checkbox/title tap targets;
- sensible metadata wrapping;
- touch-visible actions;
- mobile-aware add-item layout.

Recommended changes are mainly structural:

- Lists, Notes, Reminders and Contacts should be straightforward destinations;
- opening an individual list should produce a focused screen;
- Grocery in particular should feel like a tiny dedicated app: title, items and fast input with
  minimal surrounding chrome;
- list creation/editing should use focused sheets rather than expanding an already busy list page.

## 6.4 Tasks & rewards / Meridian

Meridian currently exposes up to eight top-level sections. A mobile picker prevents overflow but
still asks the user to navigate the domain's data structure.

Recommended primary phone model:

```text
Tasks
Rewards
My progress
More
```

Suggested grouping:

- Tasks includes ordinary tasks and routines;
- Rewards is the shop/redemption workflow;
- My progress includes goals, wishlist and leaderboard/personal progress;
- More contains management/settings and less frequent tools.

For child-facing use, optimize around three questions:

- What can I do?
- How many points do I have?
- What can I get?

Adult management/setup can remain richer but should not dominate the everyday phone screen.

## 6.5 School & study / Education

Education should become deadline- and timetable-first on mobile.

Recommended landing screen:

```text
School & study

Today
  9:00  Cyber Defence
  14:00 Lab

Due soon
  Threat Intel Lab             Tomorrow
  Assignment 2                 Friday

Assignments                    ›
Timetable                      ›
Courses                        ›
Events                         ›
```

Move Profile and Institutions into configuration/More unless immediately relevant.

Assignments should get real detail screens. Notes, files, status, priority and due date then live
inside the assignment rather than expanding into a large workspace inside the list.

Timetable should prioritize today/week agenda cards on phone. Dense desktop schedule comparison can
remain available at wider breakpoints.

## 6.6 Books

Books is a lower-priority structural change because its shelf/card model already suits mobile.

Recommended changes:

- Personal / Book Club as a simple two-state segmented control;
- clear shelf/status navigation;
- tapping a book opens a focused detail screen;
- add/edit metadata moves to a sheet;
- Add Book starts with title/ISBN/link and only then reveals optional cataloguing metadata.

The phone should feel like a reading list, not a library database editor.

## 6.7 Household guide / Home Wiki

The mobile Wiki should be extremely direct:

- Search at the top;
- Favourites and Emergency shortcuts;
- pages/categories below;
- tap a page to read it full-screen;
- Edit is an action on the page, not an inline form inside the browse list.

Emergency information should be reachable in very few taps and remain readable under stress.

## 6.8 Pets

The current pet cards already present identity well, but treatments and appointments expand inside
the card.

Give each pet a real detail screen:

```text
Milo

Next attention
Flea treatment due Saturday

Treatments        ›
Appointments      ›
Vet details       ›
History           ›
```

The Pets landing screen should show each pet and the next thing needing attention. Creation/editing
moves to focused forms.

## 6.9 Our home / Homestead

This should receive the **largest mobile redesign**.

Nine top-level sections are too many for phone tab navigation. Replace the top-level mobile tab
selector with a home dashboard and navigable rows.

Recommended landing screen:

```text
Our home

Needs attention
  2 maintenance jobs
  1 warranty expiring

Your home
  Rooms & areas             ›
  Maintenance               ›
  Appliances                ›
  Pool & spa                ›
  Power & water             ›
  Projects                  ›
  Contacts                  ›
  Costs & cover             ›
```

### Rooms and floor plan

Default phone Rooms experience should be a tile/list view:

```text
Rooms & areas

🏡 Family room
   3 plans · $1,240 remaining                ›

🛏 Master bedroom
   1 open plan                               ›

🏊 Pool
   Water check due Saturday                  ›

🛠 Shed
   2 plans                                   ›
```

Provide **View interactive floor plan** as a deliberate full-screen spatial mode. Panning/zooming is
then expected and acceptable. The floor plan must not be the only comfortable way to navigate room
information.

Room pages should become natural detail destinations for plans, purchases, notes and status.

## 6.10 Money / Solace

Solace has already improved by reducing many historical tabs to five high-level concepts: Now,
Bills, Plan, Insights and Manage. Mobile should take the next step and become action-first.

Recommended Money landing screen:

```text
Money

Safe / current position
$X available after planned commitments

Coming up
Electricity               $182   Tomorrow
Mortgage                 $2,100   18 Aug

Next pay
Friday 14 Aug
$X allocated · $Y remaining

Bills          Pay plan
Buckets        Purchases
```

Then open dedicated phone screens for:

- Bills;
- Pay plan;
- Buckets;
- Purchases;
- Insights/history;
- Manage/configuration.

`Manage` should not have the same everyday prominence as current financial position and upcoming
obligations.

Add Bill, Edit Bill, Add Bucket, Record Income and similar operations should use focused sheets or
form screens instead of expanding long forms inside the surrounding finance page.

Keep sensitive re-authentication and all finance permission boundaries unchanged.

## 6.11 Fitness & Training

Fitness is an inherently phone-in-hand workflow, so it deserves strong mobile treatment.

The live workout implementation is already headed in the correct direction:

- large set completion controls;
- editable set rows;
- previous-performance context;
- sticky Finish Workout actions.

Preserve that focus. During an active workout, reduce unrelated navigation/noise as far as practical.
The dominant content should be:

- exercise name;
- previous performance;
- current sets;
- large completion/next actions.

Program building and exercise administration are less frequent and can remain richer, preferably on
dedicated screens rather than mixed with live training.

## 6.12 Trips & holidays / Travel

Treat a trip as its own mobile project.

Recommended trip detail:

```text
Japan 2027

12–26 September
4 travellers

Next action
Book accommodation by 30 March

Itinerary                 ›
Bookings                  ›
Things to do              ›
Packing                   ›
Documents                 ›
People                    ›
```

Trip, booking and itinerary forms should use progressive focused editors rather than long inline
forms. Preserve surprise/hidden-user rules and calendar integration.

## 6.13 My Corner

My Corner should feel like a personal home/profile, not another multi-tab database page.

Overview should surface:

- personal status;
- assignments/tasks;
- points/goals where applicable;
- current wishes/lists;
- recent activity.

Activity, Assigned and Lists become drill-down destinations. Reactions can remain compact and
household-friendly.

## 6.14 Notifications

The current page is functional but reads like an administration matrix: Devices, Quiet Hours and a
long category list with separate In-app and Push switches.

Reorganize around human questions:

```text
Notifications

This phone
Push notifications               On
Chrome on Android
Test notification                  ›

When to notify me
Quiet hours                    10pm–7am
Morning reminders                 8am

What to notify me about
Appointments                       ›
Tasks & assignments                ›
Household activity                 ›
Bills                              ›
```

Rules:

- prioritize the current device;
- place other registered devices in a secondary section;
- simple switches save immediately;
- show brief `Saved` feedback rather than requiring a final page-level Save button;
- category detail can contain Push/In-app/Mine-only options;
- browser permission explanation remains contextual and explicit.

## 6.15 Manage HomeStack / Settings

The mobile Manage page should become a settings directory rather than one long page containing
household settings, stacks, version history, notifications, backups, push devices, family colour
and future controls.

Recommended structure:

```text
Manage HomeStack

Household                 ›
People & access            ›
Stacks                     ›
Backups                    ›
Push devices               ›
Appearance                 ›
Version & system           ›
```

Personal notification preferences should be accessible from the user's profile/preferences rather
than feeling like household-wide administration.

Sensitive/admin operations retain their existing permission and re-authentication requirements.

---

## 7. Mobile interaction rules for all nodes

### 7.1 Prefer routes to giant conditionally rendered pages

Use meaningful URLs for important mobile contexts so that:

- notification deep links land somewhere stable;
- Search can open exact records;
- browser/PWA Back works naturally;
- refresh retains context;
- screens can be lazy-loaded independently;
- the same record detail can be linked from Hub, Calendar, Corners and Search.

Query-string tabs can remain where they represent a true small view state, but core entities and
major sections should increasingly use dedicated routes.

### 7.2 No routine horizontal scrolling

Document-level horizontal scrolling is a defect.

Horizontal movement is acceptable only for an intentionally spatial/continuous control such as:

- the explicitly opened floor-plan viewer;
- a small segmented day/date strip;
- a deliberate chart timeline where alternatives are supplied.

Tables should become cards/rows below the desktop breakpoint unless column comparison is the point
of the screen.

### 7.3 Forms should be focused

On phones:

- common fields first;
- optional/advanced fields collapsed;
- primary action sticky when the form is long;
- destructive action visually separated;
- validation adjacent to the failing field/workflow;
- keyboard type/inputMode chosen appropriately;
- unsaved changes should not be lost accidentally where the form is substantial.

### 7.4 Save behaviour

Prefer immediate save for simple settings switches and single-value controls.

Use explicit Save for multi-field records where the user needs to review a coherent change.

Always show enough feedback to answer:

- Did it work?
- What changed?
- Is anything else required?

### 7.5 Preserve permission and sensitivity behaviour

Mobile convenience must never weaken:

- backend authorization;
- node visibility restrictions;
- sensitive re-authentication;
- private record handling;
- hidden/surprise Travel handling;
- safe notification text;
- User/Person identity rules.

UI hiding is not a security boundary.

---

## 8. Engineering execution order

The order matters. Avoid asking an implementation agent to simply “fix mobile responsiveness on all
pages”, because that will recreate page-specific solutions and leave the product inconsistent.

### Phase 1 — Define and automate the mobile contract — DONE (v0.36.0)

Primary target sizes:

- 360–430px: everyday phone design target;
- 320px: minimum/stress test;
- approximately 768px: tablet transition target.

Add Playwright/browser acceptance coverage for major routes before large layout changes:

- capture baseline screenshots;
- assert no document-level horizontal overflow;
- assert critical controls are visible/reachable;
- test major deep links;
- test modal/sheet operation with phone viewport;
- test light/dark where practical.

Create a short repeatable mobile acceptance checklist for each converted surface.

**Shipped as `frontend/playwright.config.ts` + `frontend/e2e/`** (four projects: `phone` 390×844,
`phone-dark`, `phone-stress-320`, `tablet-768`, all pinned to Chromium — the iPhone device
presets default to WebKit, which needs host system libraries not installable here without sudo;
real Safari/iOS behaviour is still Phase 10's job). Runs against the already-live dev server
rather than starting a second one. **Every test goes through `e2e/fixtures/mockApi.ts`**, which
intercepts all `/api/v1/**` requests and answers from fixtures — the dev server shares a database
with real daily use, so a genuine login/write here could touch real household records or fire a
real push notification; nothing in this suite ever reaches the real backend. Shared assertions
(`expectNoHorizontalOverflow`, `expectMinTouchTarget`) live in `e2e/fixtures/assertions.ts` for
reuse as later phases add coverage. See `frontend/e2e/README.md`.

### Phase 2 — Build shared mobile primitives — DONE (v0.36.0)

Implement the common screen/list/settings/sticky-action/form patterns described in section 5.

Refine typography and PageHeader behaviour. Establish one standard for mobile forms, action menus,
section navigation and saved feedback.

Do this before converting large nodes.

**Shipped as `frontend/src/components/mobile/`**: `MobileScreenHeader` (title + subtitle +
contextual actions for a focused subscreen; the app shell is the default owner of mobile Back,
so this only renders its own Back button behind an explicit `showBack` opt-in — corrected in the
Phase 3 pass below once a shell-level Back existed to risk duplicating), `MobileSection` (heading
+ spacing), `MobileListRow` (whole-row nav/action target — `to`, `onClick`, or static; title/
subtitle wrap to ~2 lines by default, since real content routinely needs it, with a `compact`
opt-in for the rows that genuinely need one line), `MobileSettingsRow` (immediate-save switch or
navigate-to-subpage row, extracting the `Toggle` pattern `NotificationSettingsPage` had
duplicated inline), `MobileSummaryCard` (compact attention banner), `StickyActionBar`
(safe-area-aware bottom actions, offset to clear the bottom nav — reuses the same `5.25rem`
constant `CalendarPage`'s floating add button already established), and `MobileActionMenu`
(kebab-triggered action sheet, built on the existing `Modal`). `Modal` itself gained a `size:
'full'` variant — edge-to-edge and near-viewport-height on phone, no larger than `'lg'` on
desktop — for the "full-height/focused mobile form sheet" this section calls for. **Deferred, not
built speculatively:** a standard filter/sort sheet and a standard saved/success toast — neither
has a concrete first caller yet; add them in whichever later phase actually needs one, matching
the shape that phase's real UI requires rather than guessing now.

### Phase 3 — Redesign AppShell/mobile navigation — DONE (v0.36.0)

Implement:

- simplified mobile top bar;
- fixed Home / Add / More model;
- two configurable shortcuts;
- central Quick Create;
- More directory/search/profile;
- proper detail-screen Back/context behaviour;
- safe-area and keyboard checks.

**Shipped in `frontend/src/features/web/AppShell.tsx`.** Mobile top bar: Search and Create move
out (`hidden md:flex` — desktop keeps them exactly as before, per this phase's own "desktop
sidebar behaviour can remain intact"); the destination icon is replaced by a Back button
whenever the route is nested below its stack's base route (`location.pathname !==
currentNav.route`), mobile-only. Bottom nav is now Home (fixed) → shortcut → **Add** (fixed
centre, opens the same Quick Create sheet the old top-bar button did) → shortcut → More (fixed);
`MOBILE_SHORTCUT_SLOTS = 2` replaces the old 4-slot `MOBILE_PRIMARY_SLOTS`, and Home is no longer
a choice in the "Edit bottom bar" customiser since its slot is fixed. Search remains reachable on
phone via the existing More sheet "Quick actions" row, matching this doc's §4.1 instruction
("Search should remain globally available through More"); giving it prominence on the Hub itself
is deferred to Hub's own conversion (§6.1), out of scope for a shell-only phase. Found and fixed
in passing: the top bar's Search/Create buttons were `h-10`/`min-w-10` (40px), short of this
doc's own §3.3 baseline — bumped to `h-11`/`min-w-11` (44px), the one non-shell-structural change
in this phase, made because the Playwright touch-target check written in Phase 1 caught it
immediately.

Desktop sidebar behaviour can remain intact.

**Correction pass (v0.36.1, external review before Phase 4 landed).** A review against this
document while Phase 4 was underway found several foundation gaps worth fixing before more
screens depend on this shell:

- **Back was unsafe on a cold entry.** A bare `navigate(-1)` assumes in-app history exists — untrue
  for a PWA launch, a push-notification deep link, or a pasted URL, where it could leave HomeStack
  entirely or land on an unrelated prior browser-history page. `goBack()` now compares
  `location.key` against the key captured at mount: unchanged means nothing has navigated
  client-side since landing here, so it falls back to `currentNav.route` (the stack's own base
  route) instead of trusting history. `e2e/deep-link-back.spec.ts` starts a context directly on a
  nested route (no `/hub` visit first) to prove it.
- **Two Back buttons was a real risk.** `MobileScreenHeader` (§5, Phase 2) rendered its own Back
  unconditionally; a later screen using both it and the shell's contextual Back would show two.
  The shell is now the default owner — `MobileScreenHeader` only renders Back behind an explicit
  `showBack` opt-in, documented as the exception, not the default.
- **44px touch targets, enforced past the top bar.** The notification bell (40×40), the More
  sheet's close button (36×36) and its Profile-Edit/"Edit bottom bar" buttons (40px/36px tall),
  and the shared `Modal` close button (32×32) were all under baseline; all now measure ≥44px.
  `MobileSettingsRow`'s switch keeps its compact 24px-tall visual pill but sits inside a 44×44
  hit area, per §3.3's "prefer full-row tap targets" without literally enlarging every control.
  `e2e/mobile-shell.spec.ts`'s new "shell and dialog controls meet the 44px touch-target baseline"
  test covers the shell/dialog set.
- **`Modal size="full"` needed a top safe-area too**, not just the bottom inset it already had —
  an edge-to-edge phone sheet reaches the physical top of the screen, which needs
  `env(safe-area-inset-top)` on an installed iPhone PWA/notched device the same way the bottom
  needed `env(safe-area-inset-bottom)` for the home indicator.
- **`MobileListRow` truncated to one line by default.** Real content — an assignment, a
  maintenance job, a book title — routinely needs more than one line to stay meaningful. Title/
  subtitle now `line-clamp-2` by default; a `compact` prop opts back into single-line `truncate`
  for rows that genuinely need it.
- **The More sheet had its own, second dialog-accessibility implementation** (Escape + scroll
  lock only — no focus trap, no autofocus, no restore-focus-on-close) alongside `Modal`'s fuller
  one. Extracted `useDialogA11y` (`frontend/src/components/useDialogA11y.ts`) out of `Modal` so
  both share exactly one implementation; the More sheet became its own component (`MoreSheet`,
  in `AppShell.tsx`) so it could call the hook itself — hooks can't be called conditionally
  inside a `{moreOpen && ...}` block in an always-mounted parent.
- **The bottom-bar shortcut list couldn't actually reach zero, and didn't backfill a
  since-disabled pin.** `effectiveMobileKeys` fell back to defaults whenever the saved list's
  *length* was falsy, so deliberately removing both shortcuts was indistinguishable from never
  having customised — "up to two" couldn't mean zero. A `hasCustomizedNav` ref (from whether the
  `localStorage` key exists at all, not the parsed length) now makes that distinction. Separately,
  if a household disables a node whose stack was pinned, that slot silently shrank instead of
  being replenished — a saved key no longer in `availableKeys` means its node disappeared, not
  that the user chose to drop it, so it's backfilled from the unused defaults; a saved list that's
  simply shorter than two slots (a deliberate choice) is never topped up.
- **The Hub Playwright assertion accepted `body` as a fallback** for the expected Home heading,
  which meant the test could pass even if Hub's actual content went missing. It now checks a real
  Hub-specific string.

No architectural change: still React/Tailwind/PWA, the same mocked-Playwright-API approach, the
same shared mobile primitives, the same fixed Home/Add/More bottom nav with two shortcuts.

### Phase 4 — Calendar as the reference implementation — DONE (v0.36.1)

Calendar should establish the canonical patterns for:

- date navigation;
- sheets;
- full-screen/focused editors;
- floating/sticky actions;
- mobile view switching;
- source deep links;
- Back behaviour.

Once Calendar feels polished, reuse those patterns elsewhere.

**Shipped in `frontend/src/features/web/pages/CalendarPage.tsx`.** Calendar already had solid
mobile groundwork (phone month grid, swipe navigation, the mobile view picker, a floating Add
button, the selected-day bottom sheet) — this phase refined it against §6.2 rather than replacing
it:

- **Agenda is the default view on phone**, independent of the household's own (typically
  desktop-oriented) `calendar_default_view` — computed once at mount from `window.innerWidth < 640`
  (this page's own established mobile/desktop split; the shell's is `md:`/768px, a pre-existing
  inconsistency between the two not introduced or fixed here) and never overridden by the
  household-default effect. A stored personal preference (`hs_cal_view` in `localStorage`) always
  wins over both.
- **Week is now a horizontal day strip plus the selected day's agenda**, not a squeezed
  desktop-style 7-column grid stacked into one column. Extracted `DayAgendaList` so the Day view
  and the phone Week view render the exact same list — one implementation, not two that could
  drift.
- **Month cells show a dot per event (up to three) plus an overflow count, not a truncated
  8px-tall title.** Orientation, not full content, per §6.2 — the day's actual events live one tap
  away in the existing day sheet.
- **Event create/edit is now `Modal size="full"`** — the near/full-height phone sheet with a
  sticky Save this section and Phase 2's Modal work both called for; desktop is unchanged (capped
  at the normal `'lg'` width).
- **Found and fixed in passing: `AppShell`'s `<main>` was never actually width-constrained to the
  viewport.** It's a flex item of a flex-column wrapper, and flex items default to
  `min-width: auto` — letting their content's own minimum size win over the container's, rather
  than shrinking to fit. This was latent (no existing page had a wide enough non-wrapping row to
  expose it) until Calendar's new week-day-strip did. Fixed with `min-w-0` on `<main>` and its
  flex-column parent — a shell-level fix, not something Calendar itself needed to work around, so
  every future page benefits from it, not just Calendar.

**New `e2e/calendar.spec.ts`** (mobile view defaults, the Month/Week/day-sheet interactions, the
full-sheet editor) **and new `e2e/deep-link-back.spec.ts`, plus the Phase 3 correction-pass
additions to `e2e/mobile-shell.spec.ts`** (touch-target coverage, More-sheet focus trap/restore,
the tightened Hub assertion). 20 Playwright test definitions total, 63 passing across the four
viewport projects (stable across repeated runs); `tsc --noEmit` and `npm run build` both clean.

### Phase 5 — Homestead

This removes one of the largest current phone pain points.

- replace nine-section mobile picker with home dashboard/subroutes;
- room list/tile view first;
- room detail screens;
- floor plan becomes explicit full-screen spatial mode;
- focused maintenance/appliance/project flows.

### Phase 6 — Solace / Money

- create action-first Money home;
- separate Bills/Plan/Buckets/Purchases/Insights;
- move inline editors to sheets/screens;
- preserve sensitive gate;
- ensure monetary values/status remain readable without dense dashboards.

### Phase 7 — Notifications and Settings

Establish the reusable settings-directory pattern:

- settings rows;
- immediate-save switches;
- dedicated subpages;
- current-device-first push experience;
- shorter default explanatory copy with deeper help when required.

### Phase 8 — Daily-use nodes

Convert in this order, reusing the now-stable patterns:

1. Atlas — preserve its good item/list interactions and improve navigation/detail flows;
2. Meridian — simplify kid/adult mobile hierarchy;
3. Education — today/deadline landing + assignment details;
4. Pets — pet detail model;
5. Fitness — polish focused live workout and separate management flows;
6. Corners — personal home + drill-down sections.

### Phase 9 — Lower-frequency content/planning nodes

Convert:

- Books;
- Home Wiki;
- Travel.

They should now be able to reuse the established list/detail/form/settings primitives rather than
inventing new responsive patterns.

### Phase 10 — Complete real-device acceptance

Test at minimum:

- Android Chrome in-browser;
- installed Android PWA;
- iPhone Safari/Home Screen PWA where available;
- small and larger phones;
- portrait and landscape;
- tablet/touch layout;
- light and dark mode;
- normal and increased browser/text scaling;
- keyboard-open form states;
- long household/person/node labels;
- empty/loading/error states;
- deep links from Calendar, notifications, Search and Corners;
- destructive operations;
- offline/reconnection states already supported by the PWA.

---

## 9. Acceptance criteria

HomeStack Mobile UX v1 is not complete merely because screenshots fit at 390px.

### 9.1 Global acceptance

- No accidental document-level horizontal scrolling on ordinary screens at 320px and above.
- Important destinations are normally reachable within two taps from the shell.
- Common creation is reachable globally through Add/Quick Create.
- Primary routine controls meet the approximately 44px touch-target baseline.
- Meaningful text is readable without pinch zoom.
- Fixed navigation/actions respect safe areas.
- On-screen keyboard does not obscure the active field or primary action.
- Back returns to a meaningful previous context.
- Refresh/deep-link preserves meaningful screen/record state.
- Light and dark modes remain coherent.
- Permission/sensitivity behaviour is identical in strength to desktop.

### 9.2 Everyday usability

A household member should be able to complete these quickly on a phone:

- check what needs attention today;
- open today's Calendar and an event;
- add an event;
- add/check off a grocery or list item;
- view/complete a Meridian task;
- check an assignment deadline;
- mark pet/home maintenance attention;
- see upcoming bills/current Money position if authorized;
- enable/test/configure notifications;
- find a household Wiki page;
- start and complete a Fitness workout;
- open a specific record from a push notification.

### 9.3 Navigation comprehension

A user should not need to know internal node names or remember that a feature exists under an
arbitrary tab. Plain household language and stable drill-down navigation remain the rule.

---

## 10. What not to do

Do **not**:

- rewrite HomeStack in React Native, Flutter or another frontend stack merely to fix mobile UX;
- split business logic into a separate native client;
- redesign the backend for this work unless a concrete API gap is exposed;
- throw away the current semantic tokens/brand;
- add a large third-party component framework just to obtain mobile visuals;
- fix the project by adding hundreds of isolated `sm:`/`md:` classes to current giant pages;
- use horizontal scrolling as the general answer to dense data;
- solve navigation density by converting every large tab set into a dropdown;
- hide complexity by shrinking important text;
- weaken sensitive re-authentication or permission checks for mobile convenience.

The responsive PWA architecture is capable of delivering the intended experience. The work is
primarily product hierarchy, interaction design and component composition.

---

## 11. Implementation discipline

For each screen converted:

1. identify the primary phone job before touching CSS;
2. decide the mobile screen hierarchy/index-detail flow;
3. reuse or improve a shared mobile primitive;
4. preserve existing domain/API/security behaviour;
5. add/update deep-link routes where useful;
6. add phone viewport tests before declaring the screen complete;
7. verify real-device touch/keyboard behaviour;
8. only then refine desktop/tablet regressions.

Avoid converting several large nodes simultaneously before the shared patterns are proven. Calendar
should be the first reference, then Homestead and Solace should validate that the pattern works for
large, complex domains.

---

## 12. Definition of the intended result

The programme succeeds when HomeStack stops feeling like thirteen responsive web pages sharing a
sidebar and instead feels like one mobile household application with multiple capabilities.

The user experience should be:

- **Home-first:** what matters now is visible quickly;
- **task-first:** screens are organised around actions/questions, not model structure;
- **one-handed:** common actions are easy to reach and tap;
- **progressive:** complexity appears only when needed;
- **consistent:** the same navigation/form/detail patterns recur across nodes;
- **calm:** normal household state is readable rather than dashboard-dense;
- **secure:** convenience never bypasses backend permission/sensitivity rules;
- **deep-linkable:** Calendar, Search, notifications and Corners can open exact useful contexts;
- **responsive by design:** phone is intentionally composed, not merely a narrower desktop.

The engineering principle for the programme is therefore:

> Do not make everything fit on a phone. Make the phone the best way to use HomeStack.
