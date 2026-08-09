# UI consistency audit (2026-08-09)

Recorded from a desktop pass over Home, Calendar, Lists & notes, School & study, Books,
Pets, Our home, Tasks & rewards and Money before the partner pilot. Owner-reported items are
marked **(owner)**.

Status key: `[ ]` open · `[~]` partly done · `[x]` fixed (v0.22.0–v0.23.2).

## 1. Structure and layout

- [x] **Every page was a different width.** Pages set their own container, ignoring the shell:
  `max-w-5xl` (Pets, Household guide), `max-w-7xl` (Money, School & study), unconstrained
  (the rest). Navigating between nodes moved the content box by ~600px.
  **Fixed:** one `CONTENT_CONTAINER` token in `components/PageContainer.tsx`, used by the top
  bar, `<main>` and every page; the four per-page overrides are gone.
- [x] **(owner) Page header did not align with the sidebar header.** Sidebar brand was
  `h-[76px]`, top bar `h-[62px] md:h-[68px]`, and the two used different horizontal padding
  from `<main>`. **Fixed:** both headers are now the same height and the top bar's content sits
  in the shared container, so the title column lines up with the page title below it.
- [x] **(owner) Hub left the right third empty.** The grid was `xl:grid-cols-3` while widgets
  default to `medium` = `xl:col-span-2`, so the third column was structurally always empty.
  **Fixed:** a 4-column grid at xl with 1/2/4 spans, so 4 small, 2 medium or 1 large widget
  tiles a row exactly.
- [x] **(owner) Tab pills float.** The shared `Tabs` control was an `inline-flex` pill group
  sized to its own content, so a three-tab page and a twelve-tab page had visibly different tab
  rows and neither looked attached to the content. Now a full-width underlined bar (`primary`),
  with the pill treatment kept as a `secondary` variant for a second level inside a page.
- [x] **Books is the only page with a right-hand rail.** Removed. The shelf switcher inside it
  duplicated the shelf tabs (which already carry the counts), and the remaining panels read fine
  as full-width sections beneath the grid, matching every other destination.

## 2. Duplication

- [x] **Node identity is stated twice, differently.** Once the page header stopped rendering a
  title that merely repeats the destination, the long per-page description became dead text that
  never appeared. All nine are removed; `config/stacks.ts` is now the single description a node
  has.
- [decided] **Home's H1 is a greeting while the top bar says "Home".** Keeping the greeting: a
  personal salutation on the household dashboard is deliberate warmth, and Home is the only
  page where the H1 is not a destination name. Recorded so it is not "fixed" by accident later.
- [~] **Two search boxes on every node page** (global top bar + in-node). Money no longer
  needs a **Search** button — it searches as you type on the same 300ms debounce as every other
  node, keeping only Refresh (its figures are recalculated server-side). Whether a node needs
  its own box at all, given the global one, is still open.
- [~] **Same fact twice on one screen.** Books' duplicated shelf counts are gone with the rail.
  Tasks & rewards still shows the top balance in both its tile and the Balances card, and
  Money's finance-health list still restates what the all-zero tiles say.
- [x] **Duplicate quick-capture.** Home offered two kinds where Lists offered three, so the same
  job had a different answer depending on where you started it. Home now offers To-do / Note /
  Reminder in the same order, picking a list for a to-do exactly as Lists does.
- [x] **Two copies of the node colour table and the source-link routing** (CalendarPage had its
  own `NODE_COLOUR` and `sourcePath`). **Fixed:** both now live in `lib/sourceLinks.ts`,
  shared by the Calendar and the Hub's Upcoming card.

## 3. Action language

- [~] **Five button styles with no primary/secondary rule.** "+ Add book" was primary while
  "+ Add pet" and "+ New list" were secondary — identical rank, opposite treatment.
  **Fixed:** Pets and Lists now use the primary variant. Money's coloured **View** pills and
  the remaining ad-hoc buttons across Meridian/Homestead still need a pass.
- [x] **Three destructive vocabularies:** "Delete" (Pets), bare `×` (Books, Lists), "clear"
  (Our home counters), none in the danger colour. `components/RowActions.tsx` now gives one
  Edit/Delete/Remove vocabulary with danger-toned deletes, rolled out across Pets, Books, Lists,
  School & study and Tasks & rewards. A `×` remains only for dismissing a banner, which destroys
  nothing.
- [x] **"clear" on Our home counters** read as an instruction rather than a status. Now
  "All clear" / "Needs attention".
- [ ] **Primary action placement varies:** top-right (Books, Calendar), left below tabs (Pets,
  Lists), absent (School & study, Our home, Money). Left open deliberately — moving the Pets and
  Lists add buttons into the page header means lifting form state out of the tab components, and
  that is a refactor worth doing on its own rather than at the end of a polish pass.
- ~~Home's quick-add "Add" button looks disabled.~~ **Withdrawn — not a defect.** It *is*
  disabled: the button is `disabled={!text.trim()}` and the screenshot was taken with an empty
  field. Correct behaviour.

## 4. Components

- [x] **Three stat-card layouts.** One `StatCard` (label, value, optional hint and badge) now
  serves Tasks & rewards, Our home, the room detail page and Money. Money's coloured "View"
  pills are gone — the tile itself is the link — and its 4-then-2 grid became one 3-across grid
  that tiles exactly.
- [x] **Card titles split between ALL-CAPS and sentence case.** `Card` rendered its title
  uppercase while hand-written headings beside it were sentence case. Card titles are now
  sentence case; ALL-CAPS is reserved for the small field/section labels, so the two stopped
  reading as the same thing.
- [x] **Two identical levels of pills** in Books, plus a checkbox filter in the tab row. The
  shelf row is now the `secondary` tab variant, and the filter sits under the tab bar instead of
  inside it — a filter is not a tab.
- [x] **No shared empty state.** The page-level cases (Lists search, Routines, Rewards shop) now
  use `EmptyState`. The remaining one-line "no items" strings live inside Hub widgets, which the
  backend drops entirely when empty — a full centred empty state inside a small widget would be
  the wrong shape, and it is unreachable anyway.
- [x] **Mixed radii/elevation.** Partly a bad reading on my part: search fields are already
  `rounded-xl` like every other input, not pills, and Money's tiles now use the shared `StatCard`.
  The genuine outlier was Hub widgets at `rounded-3xl` against `rounded-2xl` cards; they match
  now.
- [~] **Money's 12-tab row** now sits in the full-width underlined bar rather than a pill group
  sized to itself, so it no longer looks like a different component to Pets' three. Whether 12
  tabs is the right information architecture for Money is a separate question.

## 5. Content and semantics

- [x] **The node-description formula holds for only 5 of 8.** Pets, Books and Calendar now use
  the same "<Brand> keeps … together" shape as the rest.
- [x] **"Error" badge for incomplete Money setup** made a fresh install look broken. The badge
  now reads "Setup needed" / "Needs attention" / "Ready"; the backend status is unchanged.
- [ ] **Settings live in different places:** Tasks & rewards "Settings", Money "Manage", Our
  home a setup form on Overview.
- [x] **Mixed date formats on one page** — Home's header omitted the year while its Countdown
  widget always showed one. The Countdown now shows the year only when it isn't the current one.

## 6. Shell

- [x] **(owner) The HomeStack logo did not navigate.** Now a link to Home.
- [x] **`⌘K` shown unconditionally**, contradicting its own tooltip. Now Ctrl or ⌘ by platform.
- [x] **The top-bar calendar button was the 📅 emoji**, permanently reading "July 17". Replaced
  with a drawn icon.
- [~] **Emoji as the icon system.** Only the calendar glyph — the one that carried a wrong
  date — was replaced. Node emoji are the product's warm identity and stay for now; a proper
  icon set is a separate design decision.
- [x] **Sidebar nav looked clipped.** The last row is now faded by a mask so a half-visible
  destination reads as "scroll for more".
- [x] **Active nav label truncated only when active**, because the indicator consumed width.
  The indicator is now absolutely positioned, so the label box is identical in both states.
- [x] **Active indicator sat on the right edge**, reading as a scrollbar. Now on the left.
- [ ] **School & study opens on a dead end.** It already defaults to the signed-in user's
  Person (`personIdForUser`), so the blank state in the screenshot has another cause — needs
  reproducing on the server before a fix.
- [x] **Calendar legend row does two jobs.** The colour legend and the "use ‹ › to forecast"
  hint are now separate lines with a rule between them, so the row stops reading as one
  sentence.

## 7. Hub behaviour (owner request, 2026-08-09)

- [x] **Widget selection and organisation was tedious.** Two flat lists controlled the same
  widgets; adding one meant finding it in the admin list, toggling Disabled→Enabled, then
  scrolling back to the other list. **Fixed:** one "On your Home page" list (drag, arrows, size,
  Remove) plus one searchable "Add a card" catalogue grouped by where each card comes from.
  **Add** does the right thing for the role in a single click.
- [x] **Empty widgets occupied the board permanently.** A widget with nothing to show is now
  dropped from the Hub response entirely. Ambient widgets (clock, quick add, daily quote,
  countdown) opt out via `HubWidget.always_visible`.
- [x] **One "Upcoming" card instead of one per node.** Backed by calendar events, which already
  mirror every dated node record via the scheduling helper (D7) — so Atlas, Pets, Education,
  Homestead, Meridian and Solace aggregate in one pass with no double counting and with
  visibility/sensitivity filtering already applied. Horizons: Next 7 days / This pay cycle /
  Next 30 days, grouped by day with an Overdue group. The per-node dated widgets it subsumes are
  switched off by migration and remain re-enablable.
  *Note: pay cycles come from Solace (Money), not Meridian, so the cycle horizon appears only
  when Money is permitted and unlocked.*

## 8. Requests from real use (2026-08-09)

- [x] **Room icons had to be typed as emoji.** You had to know one existed and find it on your
  keyboard, so most rooms went unmarked. Now a grouped picker (`config/roomIcons.ts`) of
  ~30 room-appropriate icons — living, sleeping, work, utility, outside — kept generic per D15.
  An icon already saved that is not on the list is preserved as its own option.

## 9. Follow-up bugs found in use (2026-08-09)

- [x] **`datetime-local` silently discarded date-only entries.** A datetime input whose time
  half is blank is *invalid*, so `.value` is `''` rather than a partial date — filling in only
  the date saved nothing at all. This lost every bill due date the owner entered. Money's fields
  are plain date pickers; the Calendar quick-add and the class timetable, which genuinely need a
  time, use the shared `DateTimeField` so a blank time cannot void the date. No raw
  `datetime-local` input remains.
- [x] **Bills entered before v0.23.5 keep their arrears.** Settlement runs at entry, so it does
  not reach data already saved. `python manage.py settle_bill_history` reports what it would
  change and only writes with `--apply`; it settles occurrences that fell due *before the bill
  was entered*, leaving anything missed since then genuinely overdue.
- [x] **A backdated bill arrived pre-loaded with arrears.** Entering a bill with its real first
  due date backfilled every month since as unpaid. Anything already due at the moment of entry
  is now settled as paid on its own due date; only payments missed *after* entry go overdue.

- [x] **Money asked for a time on every date.** Bill due dates, subscription renewals, purchase
  target dates and paydays are all `is_all_day` records, so the eight `datetime-local` inputs
  collected a time nothing read — and one that quietly affected same-day ordering and could
  shift a late-evening entry to the next day. All are plain date pickers now, saved at local
  midnight.

- [x] **A part's quantity rejected whole numbers.** The input paired `min="0.01"` with
  `step="1"`, and a number input only accepts `min + n×step` — so 2 was invalid, the browser
  snapped to 2.01, and the part was then priced at 2.01×. Now `step="any"`. Rows saved before
  the fix keep their odd quantity until re-typed.
- [x] **A blocked product image looked like a missing one.** A picture that failed to load fell
  back to the job's type icon, which is exactly what "no picture set" shows, so a shop blocking
  hotlinks read as the link not saving. The three states are now distinct, and a blocked image
  offers to open its URL. *(A household that wants images from hotlink-protected shops would
  need the server to fetch and cache them — deliberately not done: it turns the backend into a
  fetcher of arbitrary URLs, which needs an SSRF allowlist first.)*
