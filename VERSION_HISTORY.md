# HomeStack — Version History

> **Current version: 0.34.0**
>
> Versioning: `0.X` bumps mark major milestones (new node, significant new capability).
> `0.X.Y` bumps mark smaller additions within a milestone.
>
> **Rule:** bump the version and add a row here with every push to `main`.

---

## 0.34 — Discoverability and daily navigation

### 0.34.0 — 2026-08-11 — Personal defaults, inline agenda and in-app guides
- My Corner and Education Study now resolve the signed-in User's linked Person instead of choosing
  the first alphabetic household member. Education profiles and courses select saved Institutions,
  while still offering a direct path to create one.
- Countdown widgets now store a Household-local target time, default legacy/date-only targets to
  noon and switch from days to rounded-up hours inside 48 hours. Atlas adds a combined Appointments
  & events manager and edits standalone Calendar entries or Atlas-owned to-dos through shared forms.
- Corner activity carries stable source IDs: Atlas items, Education work, Meridian tasks/wishes,
  Homestead plan items, Travel ideas and Fitness programs/sessions open their source context.
  Completed Fitness sessions can be expanded safely in Corner and open highlighted workout detail.
- Manage HomeStack now explains enabled and disabled nodes through accessible summaries and full
  guides. Every node has a discreet, dismissible guide link; admins can restore hidden links.
  Version history is available offline from a generated manifest whose check mode detects drift
  from this canonical file. **815 backend tests green; frontend production build clean;
  no migration added.**

## 0.33 — Travel planning

### 0.33.0 — 2026-08-11 — Trips, destination ideas and surprise planning
- Added the Travel node with responsive Trips and To go workflows, shared notes, People
  assignment, multiple linked images, colour/status/date planning and idempotent idea-to-trip
  conversion. Destination ideas notify permitted household members and appear in their creator's
  Corner.
- Added editable flight, accommodation and other booking components with whole-party quote/actual
  totals, booked progress, flight/stay times, references and independent component book-by dates.
  Trips and timed components mirror to Calendar; booking deadlines appear once as clearly named
  Travel tasks in Calendar, Atlas Agenda and the Hub, then resolve when booked.
- Added **Keep this a surprise** exclusions for selected linked Users. Hidden plans, bookings and
  deadlines are filtered from Travel, Calendar list/detail, Agenda, Hub, notifications, Search and
  Corners even for direct URLs, while the creator remains able to manage the plan. Added Travel,
  Scheduling and permission migrations. **813 backend tests green; frontend production build
  clean; no migration drift.**

## 0.32 — Daily coordination

### 0.32.1 — 2026-08-11 — Travel planning specification
- Promoted Travel as the next node and expanded its canonical spec into a project-like Trips/To-go
  workflow: participants, multiple images, conditional flights/accommodation, booked and quoted
  cost roll-ups, coloured Calendar status, flight times, booking deadlines in Agenda/Hub and
  destination-added notifications. Documentation only; no migration.

### 0.32.0 — 2026-08-11 — appointments, Agenda, birthdays and pool schedules
- Added explicit Calendar appointments with provider/contact fields. Calendar events now carry a
  stable kind, and Atlas Agenda projects every permitted upcoming Calendar entry except birthdays
  and holidays without copying source records.
- Due-dated Atlas list items now automatically create task-classified Calendar mirrors; edits,
  completion, reopening, deletion and parent-list deletion keep the mirror aligned.
- Added Atlas People & birthdays for external friends/relatives, plus virtual birthday occurrences
  derived from both contacts and household `Person.date_of_birth`. Calendar shows the calculated
  turning age; user management exposes household birth dates; no yearly event copies are stored.
- Pool care jobs can be independently rescheduled, changed between weekly/fortnightly/monthly or
  paused directly in Pool & spa. Existing completion data is preserved because only future schedule
  fields are updated. **810 backend tests green; frontend production build clean; migrations added
  for Scheduling and Atlas. Phone Web Push remains held behind the agreed HTTPS prerequisite.**

## 0.31 — Household Corners and smart product links

### 0.31.1 — 2026-08-11 — honest partial product previews and coordination roadmap
- Product preview now rejects common retailer security/interruption-page titles instead of saving
  them as product names. Preview actions fill blank fields only, preserving names, images, shops
  and prices already entered manually; partial responses retain independently valid metadata and
  clearly identify fields the shop withheld. Added the Harvey Norman interruption regression.
- Added future Milestone 2.6/core spec 30 for appointments and Atlas Agenda, automatic dated Atlas
  sync, birthdays/people, editable pool-care schedules and per-user/per-device PWA Web Push.
  **All link-import tests green; frontend production build clean; no migration.**

### 0.31.0 — 2026-08-11 — Corners, suggestions, reactions and price-aware links
- Added the core **My Corner / [Name]’s Corner** experience with a household switcher and
  Overview, 30-day Activity, Assigned, and Lists & wishes tabs. Enabled Atlas, Fitness,
  Meridian, Education and Homestead providers contribute permission-filtered projections while
  their source records remain authoritative.
- Added personal Atlas wish/shopping lists, household/private visibility, suggestion-only access
  for other users, owner accept/dismiss review, and grouped toggleable ❤️ 👍 🎉 💪 👏 reactions
  with bundled notifications.
- Added a bounded server-side product-link previewer with SSRF/DNS/redirect/content/size/time
  protections and per-user throttling. Confirmed Atlas and Homestead products retain provenance,
  cache images locally, and can use independent price watches without changing saved costs.
- Added a household-local 09:00 catch-up-safe scheduled watch command, compact observations,
  5% meaningful-drop/explicit-sale/target rules, deduplicated alerts, currency protection and a
  single warning after repeated failures. **Full backend suite and production frontend build
  validated; migrations added for People, Atlas, Homestead, Link Imports and permissions.**

## 0.30 — The house as a place

### 0.30.1 — 2026-08-11 — readable plan views and saved room links
- Reworked the initial all-in-one drawing into two focused views: a large connected interior plan
  and a simplified whole-property view. Shared walls, square room boundaries, subtle door/window
  cues and a dedicated details rail make the plan read like the house rather than a set of cards.
- Every space is selectable by pointer or keyboard and receives a strong filled highlight and
  glow. The details rail can open a matched room or explicitly link the space to any existing
  Homestead room; saved links persist in `floorplan_data` and the drawing adopts that room's name,
  icon and colour. Links can be moved or removed without creating duplicate room records.
- Kept name-based matching as a clearly labelled suggestion for existing data, while explicit
  links take precedence. **Frontend production build clean; room metadata persistence regression
  green; no migration.**

### 0.30.0 — 2026-08-11 — native interactive floor plan
- Added a native SVG redraw of the supplied house plans to Homestead → Rooms. It combines the
  full property arrangement (pool, cabana, shed and carport) with the detailed internal room
  divisions and dimensions, without embedding either branded real-estate image.
- The drawing inherits HomeStack paper/surface/border/accent tokens in light and dark modes,
  includes wet/outdoor visual treatments, zoom controls, keyboard/assistive labels and an
  explicit approximate-layout note so it reads as part of the app rather than an image pasted in.
- Existing Homestead rooms are matched by tolerant aliases (for example Master/Bedroom 1,
  Living/Family room and Porch/Verandah). Matched spaces use their saved icon/colour and open the
  stable room planning page; unmatched spaces remain useful plan references. Rooms now default to
  Floor plan with a secondary Room list view. **Frontend production build clean; backend unchanged
  at 794 green tests; no migration.**

## 0.29 — What the house actually uses

### 0.29.7 — 2026-08-11 — subscriptions fully absorbed and household-local cycles
- Removed the remaining Subscriptions subsection from Money. Subscription-category records now
  appear directly in Bills with every other bill; old subscription URLs redirect to Bills.
- Fixed the remaining next-cycle leak: Solace now uses the Household timezone, not the Docker
  server's UTC timezone, for pay-cycle anchors, occurrence boundaries, current-day and overdue
  comparisons. The Now endpoint also honours its explicit date parameter for deterministic use.
- Regression coverage sets the household to Australia/Brisbane while Django remains UTC and
  proves a local 12 August bill is excluded from the cycle ending 11 August. **794 backend tests
  green; frontend production build clean; no migration.**

### 0.29.6 — 2026-08-11 — exact pay-cycle boundaries and Solace-owned home bills
- Fixed bill occurrence filtering to compare aware Brisbane-local day boundaries rather than
  database UTC dates. A bill due on 12 August can no longer leak into a cycle ending 11 August;
  payday-cycle views also use their displayed start/end literally.
- Solace is now the sole financial owner for home insurance and household-service bills. Linked
  bills remain fully editable/deletable in Solace with occurrences, history, Mark paid, autopay
  and set-aside behavior; saved values refresh the read-only Homestead cards through D4 events.
- Homestead Costs & cover no longer creates or deletes finance schedules. It displays only bills
  deliberately organised there, while retaining editable house-specific policy, claims, excess
  and account metadata plus direct Solace links.
- Migration `homestead.0010` links every existing policy/cost to a Solace bill, creates missing
  bills for Homestead-only records, and preserves existing links without duplication. Dedicated
  migration, local-boundary and ownership regressions included. **794 backend tests green;
  frontend production build clean; no model drift.**

### 0.29.5 — 2026-08-11 — subscriptions are bills
- Removed the duplicate Subscription model, API, serializer, services, forecast/reminder path,
  export sheet and frontend state. The Subscriptions section and Hub widget now filter ordinary
  Bills whose category is Subscription.
- Adding a subscription now uses the full Bill form with its category fixed to Subscription, so
  every subscription has occurrences and payment history, Mark paid, autopay, pause, set-aside,
  overdue reconciliation, forecasting, reminders, Calendar, Search and export behaviour.
- Data migration `solace.0010` converts every existing active legacy Subscription into a Bill,
  preserving its renewal date as First due, recurrence, provider, amount, notes, permissions,
  timestamps and Calendar link before dropping the old table. Migration behaviour is covered by
  a dedicated regression. **792 backend tests green; frontend production build clean; no drift.**

### 0.29.4 — 2026-08-11 — corrected bill dates clear stale overdue rows
- Changing a bill's first due date, recurrence, stop date or active state now rebuilds all unpaid
  occurrences from the corrected schedule. Amount-only edits retain the existing choice between
  future and all unpaid amounts.
- Paid and skipped occurrences are historical records and are always preserved.
- Occurrence materialisation now reconciles obsolete unpaid rows as well as creating missing
  ones. Opening Now automatically repairs stale overdue rows left by older date edits, including
  rows outside its normal lookback, so the overdue badge and total correct themselves after
  deployment. **790 backend tests green; frontend production build clean; no migration.**

### 0.29.3 — 2026-08-11 — one place for subscriptions
- Bills categorised as Subscription now appear in the Subscriptions section instead of the
  ordinary Bills list. Changing their category moves them back automatically.
- The two underlying record types remain intact: bill-based subscriptions retain payment
  occurrences, Mark paid, autopay and set-aside planning, while dedicated subscriptions retain
  renewal-cycle tracking. Both are presented together with their correct edit controls.
- Added a useful combined empty state and explanation of why some subscriptions have payment
  history. **Frontend production build clean; backend unchanged at 787 tests; no migration.**

### 0.29.2 — 2026-08-11 — Solace allocation ceiling
- Active percentage bucket rules now have a transaction-safe aggregate ceiling of 100%; create
  and edit requests that would exceed it return a clear validation error without changing data.
  Inactive future rules do not consume the available percentage.
- Custom shared-income splits also reject percentage totals above 100% before replacing the
  saved split. Individual percentage inputs are constrained to 0–100%.
- Bucket and income-split editors show available/allocated percentages and disable invalid saves.
  **787 backend tests green; frontend production build clean; no migration.**

### 0.29.1 — 2026-08-10 — the logo, in the app
- **HomeStack has its own face.** The owner's three brand renders are in `brand/` as sources;
  `scripts/build_brand_assets.py` crops each to its artwork, resizes it and writes the committed
  web assets to `frontend/public/brand/`. The sources are ~1 MB each of mostly empty canvas —
  not something to download to draw a 36px logo.
- **Where each one goes:** the **mark** replaces the `◇` placeholder in the sidebar header and
  names the kiosk ambient screen; the **wordmark** sits beside it there; the **lockup** leads the
  sign-in page — one per surface, on the screen that introduces the app.
- **Browser tab, home screen and installs**: favicon at 32 and 192, an Apple touch icon drawn on
  the app's paper colour (iOS fills a transparent icon with black), and light/dark `theme-color`.
- Sizes and alt text live in one `components/Logo.tsx`, which marks the logo `aria-hidden` where
  the word "HomeStack" is already on screen beside it rather than saying the name twice.
- Checked against the warm paper *and* the dark surface at both full size and 36px.
- Documentation-and-assets change: typecheck and production build clean; no backend change, no
  migration.

### 0.29.0 — 2026-08-10 — metered water & electricity usage
- **Enter a bill, get the graphs.** A new **Power & water** tab in Our home takes a water,
  electricity, gas or other bill: the period it covers, how much was used (kWh/kL/L/m³/MJ/therms),
  what it cost in total, the provider, and whether the meter was read or estimated. Everything
  else is calculated.
- **Comparisons are per day, so they are honest.** Billing periods are not equal lengths; a
  92-day quarter beside an 88-day one would read 5% worse before anyone turned anything on. Days
  billed, usage per day, cost per day and the effective rate per unit are all derived at read
  time, so correcting a bill corrects every figure and every chart at once.
- **The two comparisons that mean something:** against the previous bill, and against a year ago —
  matched to the closest period start within 45 days of a year earlier, because utilities are
  seasonal and billing dates drift. An increase reads as a warning, a decrease as a win, with an
  arrow and words as well as colour.
- **Charts without a chart library.** One column chart per measure (never two scales in one
  frame), the latest period emphasised and directly labelled, older periods as context, estimated
  reads striped and named. Every column is focusable and announces its full figures, and each
  utility's bills are also a plain table under the charts, where they can be edited or deleted.
- **No password gate here** (owner's call): usage is household-visible like maintenance and the
  pool, while Costs & cover keeps the account and policy numbers behind re-auth. Nothing reaches
  the Calendar — a bill that has arrived is not an appointment, and its recurring account already
  owns the due date.
- Also fixed: `?tab=pool` on Our home silently fell back to Overview, because `pool` was missing
  from the page's list of valid tab keys.
- **783 backend tests green (17 new); typecheck and production build clean. New migration:
  `homestead.0009_utility_bills` — run `migrate` after deploying.**

## 0.28 — Income the way the standalone app does it

### 0.28.3 — 2026-08-10 — handover alignment
- Corrected the handover's forward-looking status from the obsolete v0.21/M4 workstream to the
  shipped v0.28 codebase: Fitness, Pools & spas, completed security maturation, current Solace
  parity and the actual migration heads are now represented.
- Replaced duplicate “build Home Assistant next” guidance with the operational dependency order:
  deploy/migrate, real-data Solace cutover, Fitness/pool checks, partner acceptance, then Home
  Assistant 5.5.0. Historical progress entries remain unchanged.
- Documentation/version metadata only; no runtime or database migration change.

### 0.28.2 — 2026-08-10 — closing the UI consistency audit
- **School & study no longer opens on a dead end.** Reproduced at last: the Profile tab it opens
  on defaults to the signed-in account's linked Person, and an admin who is not a student — or a
  partner's login — has none, so it landed on "Select a person" *with no selector to do it with*,
  because the picker only appeared when the household had more than one person. It now falls back
  to the first person, always shows the student picker so the choice can be changed or recovered,
  and gives a household with no people an empty state pointing at People & access instead of a
  "Loading profile…" that was never going to resolve.
- **One word for setting a node up.** Tasks & rewards said "Settings" where Money said "Manage"
  for the same job in the same position; both now say Manage. Our home is recorded as a different
  case rather than an inconsistency: its property record is reference content edited in place.
- **One treatment for approving and rejecting.** Tasks & rewards rendered the same decision three
  ways across two screens — filled warning, outlined warning, and bare underlined text. Approving
  is now a primary button and rejecting a ghost one, everywhere.
- **The last bare `✕` deletes are gone.** Homestead's six hand-rolled Edit/Delete pairs now use
  the shared `RowActions`, and the rewards shop's lower-case "remove" chip became a Remove action.
- **The top-balance tile is gone from Tasks & rewards** — the Balances card beneath already led
  with the same figure, and there it comes with everyone else's for comparison.
- **The two-search-boxes question is settled:** both stay, because they answer different questions,
  and every in-node box names its own scope against the top bar's "Search anything".
- `docs/UI_CONSISTENCY_AUDIT.md` now has one item left, the deferred icon-set decision.
- **766 backend tests green; typecheck and production build clean; no migration.**

### 0.28.1 — 2026-08-10 — the last three parity gaps
- **Cycle history.** Every closed-out pay cycle, newest first, with what was paid, skipped and
  left outstanding in each. HomeStack had been recording closeouts and then only ever reading the
  current or next cycle, so past ones were unreachable. The figures are recomputed from the
  occurrences in each window rather than stored, so correcting a bill later corrects the history.
- **Annual summary.** A calendar or financial year (1 July – 30 June) of bills grouped by category
  and then by the bills inside it, both ordered by cost, with paid and outstanding totals. Tapping
  a category opens its bills, which is the question that follows "why is this one so big".
- **Purchase completion.** Marking a purchase bought now raises its saved amount to the target, so
  something bought while part-saved stops reading as short of its goal. A balance already above
  the target is kept.
- Both new views sit under Insights, and links using the standalone page names land in them.
- **766 backend tests green (11 new); typecheck and production build clean; no migration.**

### 0.28.0 — 2026-08-10
- Re-read the standalone app's source line by line rather than trusting the parity checklist, and
  found three features that had never been ported. The checklist has been corrected; it had
  claimed complete parity.
- **Individual vs shared income.** Shared income belongs to the household, not a person: it is
  left out of the per-person contribution breakdown and applied to buckets after the personal
  splits, so a shared deposit can no longer inflate somebody's share.
- **Shared-income allocation modes.** `standard` flows through the usual bucket rules, `lump`
  sends the whole amount to one nominated bucket, and `custom` applies each line's percentage in
  order with one line taking the remainder. Without a remainder line the unallocated amount stays
  in the account rather than being invented into a bucket.
- **Per-person contributions are back.** Income now carries whose it is, so the pay plan reports
  what each person contributed and where it went. The importer had been flattening the owner into
  the income title, which lost the grouping entirely.
- Matched the reference engine's rule that only the first cap-to-remaining bucket may cap.
- The importer brings income scope, allocation mode and custom split lines across, and tolerates
  older standalone databases that predate the shared-income tables.
- **Still missing and now recorded:** cycle history, annual summary, and purchase completion not
  raising the saved amount to the target.
- **755 backend tests green (8 new); typecheck and production build clean; migration
  `solace.0009`.**

## 0.27 — Money you can actually run the household on

### 0.27.0 — 2026-08-10
- **Twelve tabs became five.** Money had a tab each for overview, forecast, schedule, closeout,
  pay plan, bills, buckets, subscriptions, purchases, paydays, checklist and manage — a row nobody
  could scan, where the common actions were as buried as the rare ones. They now group by the
  question being asked: **Now** (what do I owe), **Bills** (what goes out: bills, subscriptions,
  calendar), **Plan** (how pay is divided: pay plan, buckets, income, purchases), **Insights**
  (forecast, cycle closeout) and **Manage**. Links and bookmarks using the old tab names still land
  in the right place.
- **Money opens on what you owe.** It used to open on six stat tiles that only linked elsewhere,
  so marking a bill paid meant guessing which tab held it. The Now screen leads with "Due before
  next payday" — a running total, overdue flagged, and **Paid** and **Skip** on the row itself,
  matching the standalone app's dashboard that this replaces. Set-aside status, the payday
  checklist and the cycle position sit beneath it. One `/solace/now/` call backs the whole screen.
- **Buckets hold money instead of a number you overwrite.** Every change now goes through a
  `BucketEntry` — Add and Spend are the bucket's primary actions, each records what it was for,
  and the history shows the running balance. Correcting a balance by hand still works and is
  recorded as a correction, so the history keeps explaining the total. Buckets also carry a
  purpose (bills, savings, spending, planned purchases, other).
- `import_solace` now defaults to the standalone database's real location on this machine; the
  path it carried had not existed since the project moved.
- **747 backend tests green (13 new); typecheck and production build clean; migration
  `solace.0008`.**

## 0.26 — Pools & spas

### 0.26.0 — 2026-08-10
- Homestead can now look after a pool or spa (owner request). A pool records how it is sanitised,
  its surface, filter, volume and equipment notes — and those answers drive everything else.
- Adding a pool sets up the usual care jobs (skim, test, brush, vacuum, empty baskets, monthly
  full test, filter clean, salt-cell inspection, annual service), staggered so they do not all land
  on day one. They are ordinary maintenance rows, so they recur, reach the Calendar, complete and
  advance, and appear in Maintenance and the Hub like any other home job. Re-applying is idempotent
  by title, so switching to a salt cell adds only the job that switch introduces.
- Water tests record whichever readings were taken and are judged against the target band for that
  kind of pool: a salt pool is held to a higher stabiliser band, fibreglass and vinyl need less
  calcium than concrete, and a manually chlorinated pool is never asked for a salt reading. Whether
  a reading is in range is computed at read time, so corrected guidance applies to old readings.
- Every reading says what it is for and, when out of band, what to do about it — the screen is
  written for a household that has never run a pool, and says plainly that it is general guidance
  rather than a substitute for a pool-shop analysis.
- Kept general per D15: bands and schedule come from how the pool is built and sanitised.
- **734 backend tests green (16 new); typecheck and production build clean; migration
  `homestead.0008`.**

## 0.25 — Fitness & Training

### 0.25.2 — 2026-08-10 — phone navigation follow-up
- The bottom bar now answers "where am I" from anywhere. A destination without its own slot
  (Fitness, Books, Money) left nothing in the bar marked; the More button now stands in for the
  current destination, wearing its icon, colour and name until you open it.
- Money's month calendar fits a phone. It was pinned to 760px, so a phone scrolled a calendar
  sideways and never saw a week at once. Below `sm` each day carries coloured dots for what falls
  on it and the month's entries are listed beneath in order; the labelled chips return above `sm`.

### 0.25.1 — 2026-08-10 — phone interaction pass
- Form fields no longer zoom the page. Every control was below 16px, which makes iOS Safari zoom
  in on focus and never zoom back out, so filling in any form left the app oversized. Touch
  devices now get a 16px floor; the desktop scale is unchanged.
- Replaced all 43 `window.confirm` and 9 `window.prompt` boxes with in-app dialogs. The native
  ones are system alerts that name the origin, ignore the theme, cannot carry a danger tone and
  offer only OK/Cancel — every delete in the app ended in something that looked like a browser
  error. Confirmations now state the verb ("Delete pet"), stack full-width on phones with the
  destructive action away from the Cancel thumb, and prompts have a real label, placeholder and
  the numeric keypad where a number is wanted.
- Restored the primary action on phones. `PageHeader` defaulted to hiding itself on mobile, which
  took the page's own button with it — "+ Add pet", "+ New list" and "Add household login" were
  simply not reachable from a phone. The heading still steps aside for the shell's title; the
  actions never do.
- One rule for tabs on phones: up to three fit a row, more become a labelled picker. It used to
  be each page's choice, so Pets swiped a cramped row while Money got a picker.
- Money's six-column category report becomes per-category cards below `md` instead of a
  sideways-scrolling table that hid the figures.
- Raised the 9–10px text in the bottom bar and the mobile destination directory to a readable
  size, and the destination names to `text-sm`.
- **718 backend tests green; typecheck and production build clean; no migration.**

### 0.25.0 — 2026-08-10
- Added the first-class Fitness node, deliberately separate from password-gated medical Health.
- Seeded 45 common strength, running, swimming, cycling, cardio and mobility exercises, with a
  searchable extensible library and measurement/unit metadata.
- Added multi-day training programs assigned to People, immutable session snapshots, live elapsed
  timing, set completion and editable reps/weight/time/distance, plus add/drop exercises and sets
  during a workout.
- Finishing records duration, reps and strength volume; calculates heaviest weight, estimated 1RM,
  max reps, longest distance and fastest exact-distance times; publishes events and notifies other
  permitted users only for household-visible sessions.
- Added responsive Train, Programs, History, Records and Exercises screens plus a permission-aware
  recent-training Hub widget.
- Every set now opens at the weight the person actually lifted the previous time they trained that
  exercise, matched set for set and falling back to the program target only until there is history.
  Adding an exercise mid-workout prefills the same way, an extra set repeats the set just done, and
  the live screen names the session each default came from. Visibility is respected, so someone
  else's private training never prefills or appears on your screen.
- **718 backend tests green; production build clean; migration drift clean.**

## 0.24 — Security maturation (Milestone 4)

### 0.24.1 — 2026-08-09
- **Elevation expires far sooner on the kiosk.** Five minutes is a reasonable convenience on a
  personal laptop and an open door on a shared screen in a communal room, but the server had no
  way to tell the two apart. Sign-in now declares its surface, and the kiosk's window is one
  minute against the web's five. A client that does not declare itself gets the *cautious*
  window, so a future client that forgets cannot quietly be handed the generous one.
- **A locked node refuses in a way clients can act on.** Every surface used to read the prose
  message and invent its own locked state. The refusal now carries `code: "reauth_required"` and
  the node key, and one shared `SensitiveGate` replaces Money's bespoke unlock screen and
  Homestead's separate copy — so a locked area looks and behaves the same wherever you meet it,
  and "you lack permission" no longer reads like "you need to unlock".
- Six kiosk-window tests and two locked-response contract tests. **706 backend tests green;
  production build clean; no migration drift.**

### 0.24.0 — 2026-08-09
- **One gate for every sensitive node.** Solace and Homestead each carried their own copy of
  "is this locked, is the reader re-authenticated, record that they looked", and the copies had
  already drifted: Solace honoured the household's re-auth setting so an admin could turn the
  extra prompt off, while Homestead's finance surface ignored it and always asked. Both now use
  `apps/nodes/access.sensitive_node_access`, which reads the lock from the household's node
  configuration rather than from a hard-coded list of view classes.
- **Homestead's lock is now stated rather than implied.** It always demanded a password through
  hard-coded logic, so generalising the gate would have silently unlocked it; a migration marks
  the node lockable and turns the lock on, preserving the behaviour that was already in force —
  and making it something an admin can now turn off, exactly as for Money.
- **A lockable node starts locked.** Creating a household's node row defaulted the password
  prompt to off, so the first time a household enabled Money its prompt would have been disabled
  until someone noticed. The row now inherits the catalogue's sensitivity.
- **The account and permission trail is complete.** Granting Money access was recorded; creating
  a login, changing an access level, resetting a PIN or password, deactivating an account, and
  granting, denying or clearing a permission override were not — the most security-relevant
  actions in the product were the least traceable. All are audited now, with the acting user
  attributed. Credential *values* are never written: only that they changed, and by whom.
- **Primary actions sit where you expect.** The Pets and Lists add buttons moved into the page
  header alongside Books and Calendar, which needed lifting the form state out of their tab
  components — the last open item from the UI audit. **698 backend tests green (18 new,
  permission-first); production build clean; no migration drift.**

## 0.23 — Multi-person assignment

### 0.23.6 — 2026-08-09
- **`settle_bill_history` repairs bills entered before v0.23.5.** Settlement runs when a bill is
  created, so it could not reach the ones already saved with years of arrears. The command
  reports what it would change and writes only with `--apply`. It settles occurrences that fell
  due *before the bill was entered*; a payment missed since then is real and stays overdue.
- **Quick capture is the same everywhere.** Home offered Reminder and Note where Lists offered
  To-do, Note and Reminder, so the same job had a different answer depending on where you started
  it. Home now offers all three in the same order and picks a list for a to-do exactly as Lists
  does.
- **A node has one description again.** Once the page header stopped repeating a title the top
  bar already shows, each node's long per-page description became text that never rendered. All
  nine are gone; `config/stacks.ts` is the single source.
- **Shared empty states** on the Lists search, Routines and Rewards shop, and **Hub widgets now
  use the same corner radius as every other card** — the one genuine radius outlier.
  **680 backend tests green; production build clean; no migration drift.**

### 0.23.5 — 2026-08-09
- **Entering a bill no longer invents a backlog of arrears.** Giving a bill its real first due
  date — often months or years back, because the household has been paying it for years —
  backfilled every month since as unpaid, so a correct answer produced a wall of overdue
  warnings and dragged the unpaid total and finance health down with it. Anything already due
  when a bill is first entered is now recorded as paid on its own due date. This applies only at
  entry: a payment missed after that is genuine and still shows as overdue.
- **The last three date-and-time inputs are gone.** A `datetime-local` input whose time half is
  blank is invalid, so its value is an empty string, not a partial date — filling in only the
  date silently saved nothing. That is what lost the bill due dates in v0.23.4, and the Calendar
  quick-add and the class timetable had the same trap. All three now use the shared date/time
  field, which keeps the date and time separate so a blank time can never void the date.
- Five regression tests pin the bill due-date contract (past, future, recurring, organised into
  Homestead, and added to an existing bill) and four pin the settlement rule. **676 backend
  tests green; production build clean; no migration drift.**

### 0.23.4 — 2026-08-09
- **Money asks for a date, not a date and time.** A bill's due date, a subscription renewal, a
  planned purchase's target date and a payday are all stored as all-day records — every one of
  those models defaults `is_all_day` to true — so the forms were collecting a time nothing
  reads. All eight fields are now plain date pickers, and a date is saved at local midnight.
  A stray time was not harmless: two bills on the same day sorted by whatever time happened to
  be typed, and a late-evening time could land on the neighbouring day once converted.
  **667 backend tests green; production build clean; no migration drift.**

### 0.23.3 — 2026-08-09
- **Room icons are picked, not typed.** Creating a room asked you to type an emoji, which meant
  knowing one existed and finding it on your keyboard — so most rooms went unmarked. There is
  now a grouped list of about thirty room-appropriate icons (living, sleeping and bathing, work
  and hobbies, utility and storage, outside), kept generic rather than specific to this
  household. An icon already saved that is not on the list stays available.
- **One vocabulary for destroying things, everywhere.** The bare `×` is gone from Books, Lists,
  School & study and Tasks & rewards; they use the same danger-toned Edit / Delete / Remove
  actions Pets already had. A `×` now only ever dismisses a banner, which destroys nothing.
- **Card titles are sentence case.** `Card` rendered its title in ALL-CAPS while hand-written
  headings beside it were sentence case, so the two read as different kinds of thing. ALL-CAPS
  is now reserved for the small field and section labels.
- **Money searches as you type**, on the same 300ms debounce as every other node, instead of
  asking for a button press. Refresh stays — Money is the one page whose figures are
  recalculated server-side and worth re-pulling on demand.
- **Smaller tidies:** the Calendar's colour legend and its "use ‹ › to forecast" hint are
  separate lines rather than one row doing two jobs, and Books' filter checkbox sits below the
  tab bar instead of inside it. **667 backend tests green; production build clean; no migration
  drift.**

### 0.23.2 — 2026-08-09
- **Tabs are one control again.** The shared tab row was a pill group sized to its own content,
  so a three-tab page and a twelve-tab page had visibly different tab bars and neither looked
  attached to the content beneath. It is now a full-width underlined bar, with the pill
  treatment kept as a second-level variant — so Books' shelf row finally reads as nested inside
  its My books / Book clubs tabs instead of looking like a second copy of them.
- **One stat card.** Tasks & rewards, Our home, the room detail page and Money had four
  arrangements of the same "headline number with a label". A single `StatCard` now serves all
  of them. Money's coloured "View" pills are gone — the tile itself is the link — and its
  4-then-2 tile grid became one 3-across grid that tiles exactly instead of leaving a gap.
- **Books drops its right-hand rail**, the only one in the app. Its shelf switcher duplicated
  the shelf tabs, which already carry the counts; the remaining panels are now full-width
  sections beneath the grid like every other destination.
- **Every destination describes itself the same way** — Pets, Books and Calendar now use the
  "<Brand> keeps … together" shape the other five already used.
- **Fixed: a part's quantity rejected whole numbers.** The input paired `min="0.01"` with
  `step="1"`, and a number input only accepts `min + n×step`, so 2 was invalid, the browser
  snapped to 2.01, and the part was priced at 2.01×. Parts saved before this keep their odd
  quantity until re-typed.
- **Fixed: a blocked product image looked like a missing one.** A picture that failed to load
  fell back to the job's type icon — exactly what "no picture" shows — so a shop refusing
  hotlinks read as the link not saving. The three states are now distinct and a blocked image
  offers to open its URL. **667 backend tests green; production build clean; no migration
  drift.**

### 0.23.1 — 2026-08-09
- **A room job is now either a single item or a project.** Its products meant one thing —
  alternatives you compare and pick one of — which could not represent "everything the desk
  setup needs". A job now carries a mode: **Single item**, where products are alternatives and
  the chosen one's price is the estimate, or **Project**, where products are parts that are all
  required and their prices sum. Same rows and same add-form; only the arithmetic and the
  wording change.
- **A project's estimate is always the sum of its parts.** The manual quantity/unit-cost fields
  are hidden for a project, so there is no separately typed figure to go stale, and room and
  whole-house totals follow the parts automatically. Marking a part "chosen" no longer rewrites
  a project's estimate — that would understate a job whose parts are all needed.
- **Parts tick off as bought.** Marking one asks what it actually cost (blank keeps the
  estimate), and the job reads "3 of 5 bought · $700 spent, $250 to go". A bought part shows the
  price paid beside its name.
- Existing jobs stay single items, which is what they already were. **667 backend tests green
  (9 new, covering the two modes' maths); production build clean; no migration drift.**

### 0.23.0 — 2026-08-09
- **Anything can be assigned to several people.** An assignment was a single
  `assigned_to_person` where null meant "the whole household", so "both of us" could not be
  said at all. Every assignable record now carries an `assigned_to_people` set: empty means the
  whole household, one or more people means each of them. Applied in one pass across all nine
  assignable models — Lists items, Calendar events, Meridian tasks and routines, Education
  assessments and events, and Homestead maintenance, improvements and room plan items — so a
  picker never accepts several people on one screen and silently keeps one on another.
- **The picker is a multi-select.** "Whole family" remains the one-tap default; individual
  people are checkboxes. A chosen set reads as a name, "Ana + Bo", or "3 people".
- **Filters match any assignee.** Asking the Calendar for one person's events returns anything
  they share, exactly once. Meridian task availability, the Hub's "my tasks", and Education's
  per-student lists all treat assignment as membership rather than equality; an unassigned
  Meridian task remains open to anyone.
- **Calendar sync carries the set (D7).** `get_calendar_data()` now returns
  `assigned_to_person_ids`, and the scheduling helper applies them after the row exists. Services
  set assignees before syncing, so the mirrored event never lags its source record.
- Existing single assignees are copied into the new relation by migration before the old column
  is dropped, so nothing loses its owner. Reverse restores a sole assignee; a record shared by
  several people cannot round-trip, which is recorded in the migration.
- **The duplicated page header is gone on desktop.** The shell's top bar names and describes the
  destination, and each page repeated the same words directly beneath it. A page whose title
  just restates the destination now renders its actions only; pages with genuinely different
  context — a room name, Home's greeting — keep their heading. **658 backend tests green (6 new,
  permission-first); production build clean; no migration drift.**

## 0.22 — Attention-driven Hub and shell consistency

### 0.22.1 — 2026-08-09
- **Room jobs carry a shopping list, not one link.** A room plan item held a single `link_url`,
  which could not answer "which of the three sofas were we looking at?". Each job now has any
  number of options, and each option records what it is, a link to it, the shop, the quantity and
  price, and a picture. Marking one **Chosen** copies its price onto the job, so room and
  whole-house estimates follow the option actually picked, and only one option stays chosen at a
  time. Re-pricing the chosen option updates the estimate too.
- **Images are links, not uploads.** `image_url` stores a remote address, so adding a picture is a
  copy-paste of a product photo's URL rather than a download-then-upload round trip. A link that
  fails to load falls back to the job's type icon instead of a broken-image glyph, and images are
  requested with `referrerPolicy="no-referrer"`. Note that displaying one does make the viewer's
  browser fetch it from that third-party host.
- **Link fields are scheme-checked.** Both the product link and the image link must start with
  `http://` or `https://`; these render as `href`/`src`, so a `javascript:` URL saved here would
  otherwise run in another household member's session.
- The existing `link_url` on each plan item is migrated into a chosen option so no saved link is
  lost, then removed — two places to store a link is how they drift apart. **652 backend tests
  green (10 new, permission-first); production build clean; no migration drift.**

## 0.24 — Security maturation (Milestone 4)

### 0.24.1 — 2026-08-09
- **Elevation expires far sooner on the kiosk.** Five minutes is a reasonable convenience on a
  personal laptop and an open door on a shared screen in a communal room, but the server had no
  way to tell the two apart. Sign-in now declares its surface, and the kiosk's window is one
  minute against the web's five. A client that does not declare itself gets the *cautious*
  window, so a future client that forgets cannot quietly be handed the generous one.
- **A locked node refuses in a way clients can act on.** Every surface used to read the prose
  message and invent its own locked state. The refusal now carries `code: "reauth_required"` and
  the node key, and one shared `SensitiveGate` replaces Money's bespoke unlock screen and
  Homestead's separate copy — so a locked area looks and behaves the same wherever you meet it,
  and "you lack permission" no longer reads like "you need to unlock".
- Six kiosk-window tests and two locked-response contract tests. **706 backend tests green;
  production build clean; no migration drift.**

### 0.24.0 — 2026-08-09
- **One gate for every sensitive node.** Solace and Homestead each carried their own copy of
  "is this locked, is the reader re-authenticated, record that they looked", and the copies had
  already drifted: Solace honoured the household's re-auth setting so an admin could turn the
  extra prompt off, while Homestead's finance surface ignored it and always asked. Both now use
  `apps/nodes/access.sensitive_node_access`, which reads the lock from the household's node
  configuration rather than from a hard-coded list of view classes.
- **Homestead's lock is now stated rather than implied.** It always demanded a password through
  hard-coded logic, so generalising the gate would have silently unlocked it; a migration marks
  the node lockable and turns the lock on, preserving the behaviour that was already in force —
  and making it something an admin can now turn off, exactly as for Money.
- **A lockable node starts locked.** Creating a household's node row defaulted the password
  prompt to off, so the first time a household enabled Money its prompt would have been disabled
  until someone noticed. The row now inherits the catalogue's sensitivity.
- **The account and permission trail is complete.** Granting Money access was recorded; creating
  a login, changing an access level, resetting a PIN or password, deactivating an account, and
  granting, denying or clearing a permission override were not — the most security-relevant
  actions in the product were the least traceable. All are audited now, with the acting user
  attributed. Credential *values* are never written: only that they changed, and by whom.
- **Primary actions sit where you expect.** The Pets and Lists add buttons moved into the page
  header alongside Books and Calendar, which needed lifting the form state out of their tab
  components — the last open item from the UI audit. **698 backend tests green (18 new,
  permission-first); production build clean; no migration drift.**

## 0.23 — Multi-person assignment

### 0.23.6 — 2026-08-09
- **`settle_bill_history` repairs bills entered before v0.23.5.** Settlement runs when a bill is
  created, so it could not reach the ones already saved with years of arrears. The command
  reports what it would change and writes only with `--apply`. It settles occurrences that fell
  due *before the bill was entered*; a payment missed since then is real and stays overdue.
- **Quick capture is the same everywhere.** Home offered Reminder and Note where Lists offered
  To-do, Note and Reminder, so the same job had a different answer depending on where you started
  it. Home now offers all three in the same order and picks a list for a to-do exactly as Lists
  does.
- **A node has one description again.** Once the page header stopped repeating a title the top
  bar already shows, each node's long per-page description became text that never rendered. All
  nine are gone; `config/stacks.ts` is the single source.
- **Shared empty states** on the Lists search, Routines and Rewards shop, and **Hub widgets now
  use the same corner radius as every other card** — the one genuine radius outlier.
  **680 backend tests green; production build clean; no migration drift.**

### 0.23.5 — 2026-08-09
- **Entering a bill no longer invents a backlog of arrears.** Giving a bill its real first due
  date — often months or years back, because the household has been paying it for years —
  backfilled every month since as unpaid, so a correct answer produced a wall of overdue
  warnings and dragged the unpaid total and finance health down with it. Anything already due
  when a bill is first entered is now recorded as paid on its own due date. This applies only at
  entry: a payment missed after that is genuine and still shows as overdue.
- **The last three date-and-time inputs are gone.** A `datetime-local` input whose time half is
  blank is invalid, so its value is an empty string, not a partial date — filling in only the
  date silently saved nothing. That is what lost the bill due dates in v0.23.4, and the Calendar
  quick-add and the class timetable had the same trap. All three now use the shared date/time
  field, which keeps the date and time separate so a blank time can never void the date.
- Five regression tests pin the bill due-date contract (past, future, recurring, organised into
  Homestead, and added to an existing bill) and four pin the settlement rule. **676 backend
  tests green; production build clean; no migration drift.**

### 0.23.4 — 2026-08-09
- **Money asks for a date, not a date and time.** A bill's due date, a subscription renewal, a
  planned purchase's target date and a payday are all stored as all-day records — every one of
  those models defaults `is_all_day` to true — so the forms were collecting a time nothing
  reads. All eight fields are now plain date pickers, and a date is saved at local midnight.
  A stray time was not harmless: two bills on the same day sorted by whatever time happened to
  be typed, and a late-evening time could land on the neighbouring day once converted.
  **667 backend tests green; production build clean; no migration drift.**

### 0.23.3 — 2026-08-09
- **Room icons are picked, not typed.** Creating a room asked you to type an emoji, which meant
  knowing one existed and finding it on your keyboard — so most rooms went unmarked. There is
  now a grouped list of about thirty room-appropriate icons (living, sleeping and bathing, work
  and hobbies, utility and storage, outside), kept generic rather than specific to this
  household. An icon already saved that is not on the list stays available.
- **One vocabulary for destroying things, everywhere.** The bare `×` is gone from Books, Lists,
  School & study and Tasks & rewards; they use the same danger-toned Edit / Delete / Remove
  actions Pets already had. A `×` now only ever dismisses a banner, which destroys nothing.
- **Card titles are sentence case.** `Card` rendered its title in ALL-CAPS while hand-written
  headings beside it were sentence case, so the two read as different kinds of thing. ALL-CAPS
  is now reserved for the small field and section labels.
- **Money searches as you type**, on the same 300ms debounce as every other node, instead of
  asking for a button press. Refresh stays — Money is the one page whose figures are
  recalculated server-side and worth re-pulling on demand.
- **Smaller tidies:** the Calendar's colour legend and its "use ‹ › to forecast" hint are
  separate lines rather than one row doing two jobs, and Books' filter checkbox sits below the
  tab bar instead of inside it. **667 backend tests green; production build clean; no migration
  drift.**

### 0.23.2 — 2026-08-09
- **Tabs are one control again.** The shared tab row was a pill group sized to its own content,
  so a three-tab page and a twelve-tab page had visibly different tab bars and neither looked
  attached to the content beneath. It is now a full-width underlined bar, with the pill
  treatment kept as a second-level variant — so Books' shelf row finally reads as nested inside
  its My books / Book clubs tabs instead of looking like a second copy of them.
- **One stat card.** Tasks & rewards, Our home, the room detail page and Money had four
  arrangements of the same "headline number with a label". A single `StatCard` now serves all
  of them. Money's coloured "View" pills are gone — the tile itself is the link — and its
  4-then-2 tile grid became one 3-across grid that tiles exactly instead of leaving a gap.
- **Books drops its right-hand rail**, the only one in the app. Its shelf switcher duplicated
  the shelf tabs, which already carry the counts; the remaining panels are now full-width
  sections beneath the grid like every other destination.
- **Every destination describes itself the same way** — Pets, Books and Calendar now use the
  "<Brand> keeps … together" shape the other five already used.
- **Fixed: a part's quantity rejected whole numbers.** The input paired `min="0.01"` with
  `step="1"`, and a number input only accepts `min + n×step`, so 2 was invalid, the browser
  snapped to 2.01, and the part was priced at 2.01×. Parts saved before this keep their odd
  quantity until re-typed.
- **Fixed: a blocked product image looked like a missing one.** A picture that failed to load
  fell back to the job's type icon — exactly what "no picture" shows — so a shop refusing
  hotlinks read as the link not saving. The three states are now distinct and a blocked image
  offers to open its URL. **667 backend tests green; production build clean; no migration
  drift.**

### 0.23.1 — 2026-08-09
- **A room job is now either a single item or a project.** Its products meant one thing —
  alternatives you compare and pick one of — which could not represent "everything the desk
  setup needs". A job now carries a mode: **Single item**, where products are alternatives and
  the chosen one's price is the estimate, or **Project**, where products are parts that are all
  required and their prices sum. Same rows and same add-form; only the arithmetic and the
  wording change.
- **A project's estimate is always the sum of its parts.** The manual quantity/unit-cost fields
  are hidden for a project, so there is no separately typed figure to go stale, and room and
  whole-house totals follow the parts automatically. Marking a part "chosen" no longer rewrites
  a project's estimate — that would understate a job whose parts are all needed.
- **Parts tick off as bought.** Marking one asks what it actually cost (blank keeps the
  estimate), and the job reads "3 of 5 bought · $700 spent, $250 to go". A bought part shows the
  price paid beside its name.
- Existing jobs stay single items, which is what they already were. **667 backend tests green
  (9 new, covering the two modes' maths); production build clean; no migration drift.**

### 0.23.0 — 2026-08-09
- **Anything can be assigned to several people.** An assignment was a single
  `assigned_to_person` where null meant "the whole household", so "both of us" could not be
  said at all. Every assignable record now carries an `assigned_to_people` set: empty means the
  whole household, one or more people means each of them. Applied in one pass across all nine
  assignable models — Lists items, Calendar events, Meridian tasks and routines, Education
  assessments and events, and Homestead maintenance, improvements and room plan items — so a
  picker never accepts several people on one screen and silently keeps one on another.
- **The picker is a multi-select.** "Whole family" remains the one-tap default; individual
  people are checkboxes. A chosen set reads as a name, "Ana + Bo", or "3 people".
- **Filters match any assignee.** Asking the Calendar for one person's events returns anything
  they share, exactly once. Meridian task availability, the Hub's "my tasks", and Education's
  per-student lists all treat assignment as membership rather than equality; an unassigned
  Meridian task remains open to anyone.
- **Calendar sync carries the set (D7).** `get_calendar_data()` now returns
  `assigned_to_person_ids`, and the scheduling helper applies them after the row exists. Services
  set assignees before syncing, so the mirrored event never lags its source record.
- Existing single assignees are copied into the new relation by migration before the old column
  is dropped, so nothing loses its owner. Reverse restores a sole assignee; a record shared by
  several people cannot round-trip, which is recorded in the migration.
- **The duplicated page header is gone on desktop.** The shell's top bar names and describes the
  destination, and each page repeated the same words directly beneath it. A page whose title
  just restates the destination now renders its actions only; pages with genuinely different
  context — a room name, Home's greeting — keep their heading. **658 backend tests green (6 new,
  permission-first); production build clean; no migration drift.**

## 0.22 — Attention-driven Hub and shell consistency

### 0.22.0 — 2026-08-09
- **The Hub only carries what needs attention.** A widget with nothing to show is dropped from
  the Hub response instead of rendering a card that says "Nothing due". Ambient widgets (clock,
  quick add, daily quote, countdown) opt out through the new `HubWidget.always_visible` flag, so
  the board never empties itself completely.
- **One "Upcoming" card replaces a card per node.** It reads calendar events — which already
  mirror every dated household record via the scheduling helper (D7) — so Lists, Pets, School &
  study, Our home, Tasks & rewards and Money aggregate in a single pass with no double counting
  and with visibility/sensitivity filtering already applied. Items group by day under Overdue /
  Today / Tomorrow / weekday, and the horizon switches between Next 7 days, This pay cycle (when
  Money is permitted and unlocked) and Next 30 days without a round trip. A migration enables it
  and switches off the nine per-node dated widgets it subsumes; they stay re-enablable.
- **Choosing Hub cards is one action in one place.** "Tune this page" is now a single "On your
  Home page" list (drag, arrow moves, width, Remove) plus a searchable "Add a card" catalogue
  grouped by originating destination. Previously the same widget appeared in two flat lists and
  adding one meant toggling it in the admin list then finding it again in the personal list.
- **The Hub grid tiles.** The board was a 3-column grid whose widgets defaulted to a 2-column
  span, so the third column was structurally always empty. It is now 4 columns at desktop with
  1/2/4 spans, so same-size widgets fill a row exactly.
- **One content column for the whole app.** Pages set their own `max-w-5xl` / `max-w-7xl` / no
  constraint, moving the content box by ~600px between destinations. A single
  `CONTENT_CONTAINER` token now drives the top bar, `<main>` and every page.
- **The two headers line up.** The sidebar brand block was 76px tall against a 62/68px top bar,
  with different padding again in `<main>`. Both headers now share a height and the top bar's
  content sits in the shared container, so its title aligns with the page title beneath it.
- **Shell corrections:** the HomeStack logo navigates to Home; the search hint shows Ctrl or ⌘
  by platform instead of always ⌘ (contradicting its own tooltip); the top-bar calendar button is
  a drawn icon rather than the 📅 emoji, which permanently displayed 17 July; the sidebar's
  active indicator moved to the left edge and is absolutely positioned, so labels no longer
  truncate and jitter only on the current page; and the nav list fades its last row so a
  half-visible destination reads as "scroll for more" rather than a clipped layout.
- **One vocabulary for row actions.** `RowActions` provides Edit / Delete / Remove with
  danger-toned deletes, replacing a mix of the word "Delete", a bare `×` and a "clear" chip;
  applied to Pets. Our home's counters read "All clear" / "Needs attention" instead of "clear",
  Money's health badge reads "Setup needed" instead of "Error" on an unconfigured household, and
  Pets and Lists use the primary button variant for their add actions, matching Books.
- **Deduplicated node metadata.** The Calendar's private node-colour table and source-link
  routing moved to `lib/sourceLinks.ts`, shared with the Hub's Upcoming card.
- **Audit recorded.** `docs/UI_CONSISTENCY_AUDIT.md` lists every finding from the desktop pass
  with its status; the open items are the tab-pill treatment, duplicated node identity, stat-card
  and empty-state rollout, and the Books rail. **642 backend tests green; production build clean;
  no migration drift.**

## 0.21 — Controlled partner household pilot

### 0.21.0 — 2026-08-09
- **Partner access without over-privileging** — the account flow now recommends Household manager
  for a trusted adult, explains each role, labels PIN/password fields and can link one existing
  Person. Money/home-finance access is an explicit per-user choice rather than requiring the
  partner to become an administrator; it requires an adult password, is forbidden for child
  accounts and records an immutable audit event. Child logins are constrained to the Household
  member role so adult read access cannot be assigned accidentally.
- **Every visible destination is usable** — the node catalogue now reports whether the current
  account can view each node. Navigation, routes, global discovery and Hub contributions require
  both household enablement and user access, so a manager without Money permission no longer sees
  a finance destination or finance widgets that end in a denial.
- **One mobile hierarchy across nodes** — the shared page header avoids repeating the shell's
  destination name on first-level phone screens while retaining unique contextual headers and
  actions. Books uses shared search, tabs and labelled forms, reports failed actions clearly,
  confirms destructive removals and provides full-size touch controls; blank finance empty-state
  guidance was corrected; Lists/Tasks refinements from v0.20.4 are included.
- **Reward and allowance management are phone-native** — managers use information-complete cards
  for reward requests and weekly allowances below the desktop breakpoint, with large actions and
  progressively disclosed reward rules. Efficient comparison tables remain on larger screens.
- **Daily supporting workflows no longer fail silently** — Goals, Wishlist and Routines show API
  failures, label creation fields and use touch-sized destructive/approval controls. Pets adds
  labelled create/edit flows plus update/delete controls for treatments and appointments, while
  Household guide applies the same labelled, touch-friendly pattern to pages and categories.
- **Cross-node permissions continue inside a destination** — a manager without Money access no
  longer sees Homestead's Costs & cover section, Track cost action or links into protected Solace
  records. Existing backend permission, password re-authentication and audit gates remain the
  authority; the UI now presents the same boundary without dead ends.
- **An honest pilot gate** — `docs/PARTNER_PILOT_READINESS.md` defines account setup, acceptance
  criteria, implemented-node core workflows, single-entry ownership and the real-device checks
  still required before calling the household rollout accepted.
- No database migration required; the Money grant uses the existing per-user permission model.
- Validation: **636 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.20 — Forecastable rotating Calendar schedules

### 0.20.4 — 2026-08-09
- **Task management designed for phones** — managers now see readable task cards below the large
  breakpoint instead of a 780px table squeezed into horizontal scrolling. Each card keeps owner,
  category, points, status, recurrence and description legible, with large approval controls and
  progressive secondary management actions. Desktop retains the efficient full table.
- **A real responsive task editor** — mobile editing now happens inline in a labelled card form.
  Creating a task asks only for its name, points and eligible person first; schedule, category,
  completion rules and hot-task options remain available in a clearly named advanced section.
- **Lists use their narrow width better** — item titles may wrap, assignment and due information
  sit together beneath the title, and delete remains a distinct touch target rather than forcing
  every piece of metadata onto one line.
- **Less first-screen clutter** — Lists quick capture is one clear launcher on phones and expands
  only when needed. Lists and Tasks rely on the shell's existing mobile destination heading rather
  than repeating a second large page title, and Tasks now uses the shared searchable field.
- **A calmer rewards overview** — the three summary metrics use a compact two-column phone layout
  while keeping the approvals total prominent.
- No database migration required.
- Validation: frontend TypeScript check and production build clean; backend unchanged from the
  **624-test** v0.20.0 baseline.

### 0.20.3 — 2026-08-09
- **A true app-style phone Month view** — the complete six-week month grid is now the primary
  mobile surface and runs edge-to-edge for useful day-cell width. It no longer grows into a
  permanent selected-day panel or duplicates the month as an agenda beneath the calendar.
- **Useful information stays inside the month** — each occupied date shows its first event as a
  tiny person/source-coloured label plus a `+N` count for additional events. The separate narrow
  shared-care strip, Today treatment, selected-date outline and changed-day `S` marker remain
  clear without colouring the whole day.
- **Details without losing the month** — tapping a date opens a touch-friendly bottom sheet with
  its care state, events, times and locations. Users can open full Day view, edit a changed care
  date or add an event, then return to the unchanged Month view.
- **More calendar, less chrome** — duplicate mobile page actions were removed, creation moved to
  a familiar floating add button and rotation management remains available from Filter. Swipe,
  arrow, Today and view-picker navigation are all retained.
- No database migration required.
- Validation: frontend TypeScript check and production build clean; backend unchanged from the
  **624-test** v0.20.0 baseline.

### 0.20.2 — 2026-08-09
- **Month context stays visible on phones** — tapping a date now selects it in place and opens a
  useful day preview beneath the month instead of immediately replacing the month with Day view.
  The preview shows rotations, event times, locations and direct actions to add an event or open
  the full day.
- **Faster mobile month browsing** — swipe horizontally to move between months, jump back to
  Today without losing the selected-date model and tap dimmed edge dates to move naturally into
  the adjacent month. Month arithmetic now clamps safely at month end instead of potentially
  skipping a short month from the 29th–31st.
- **A clearer small-screen grid** — the selected date is unmistakable, event counts are replaced
  by up to three person/source-coloured dots, and the care-state colour remains a narrow strip at
  the top of each otherwise-neutral cell. Changed days retain the labelled `S` marker.
- **Less cramped controls and setup** — phones use one accessible Calendar-view picker beside
  Filter; the selected period gets the available width; quick-add wording is shorter; and the
  14-night rotation editor uses a nearby colour legend plus compact weekday/date tiles rather
  than squeezing full state labels into seven narrow columns.
- The full monthly event agenda remains available in a collapsed section without overwhelming
  the primary month-and-selected-day flow.
- No database migration required.
- Validation: frontend TypeScript check and production build clean; backend unchanged from the
  **624-test** v0.20.0 baseline.

### 0.20.1 — 2026-08-09
- **One household, one navigation language** — the shell now leads with plain-language
  destinations such as Lists & notes, School & study, Household guide, Tasks & rewards and
  Money. Node brands remain visible as supporting context without making household members learn
  internal product names before they can find something.
- **A calmer desktop workspace** — the wider sidebar groups destinations by purpose, gives each
  one a short explanation and keeps the current location visible in a clearer sticky header.
  Search and quick-create are easier to recognise, while shared page headings and tabs have a
  stronger, more consistent hierarchy.
- **A complete mobile directory** — the bottom bar retains four personal shortcuts, while More
  now provides a descriptive directory of every available destination and a clearer editor for
  choosing those shortcuts. Profile, search, create, theme and account actions live in the same
  predictable sheet.
- **Home is useful rather than repetitive** — duplicate phone navigation cards were removed from
  the Hub so it concentrates on household widgets. Desktop widgets can use a roomier three-column
  grid and retain the fast drag-and-drop arrangement introduced in v0.19.2.
- **Responsive Calendar polish** — period navigation, view selection and filters now sit in one
  calmer responsive toolbar without changing the rotating-schedule forecast or its narrow colour
  strips.
- No database migration required.
- Validation: frontend TypeScript check and production build clean; backend unchanged from the
  **624-test** v0.20.0 baseline.

### 0.20.0 — 2026-08-09
- **Enter the cycle once** — Calendar supports an anchored, reusable two-state rotation instead
  of one event per day. The setup is pre-filled with the requested 2/2/3/2/2/3 shared-care
  sequence, while labels, colours, People and every day remain editable for other households and
  uses such as shift work.
- **Forecast indefinitely without database growth** — occurrences are calculated only for the
  visible range from one canonical pattern. No daily `CalendarEvent` rows or duplicate dates are
  generated.
- **Change one day safely** — tapping a rotation badge can swap just that date, keep an optional
  note and visibly mark it as changed. “Restore repeating plan” removes the exception without
  touching the underlying cycle.
- **Continuous two-colour month forecast** — desktop and mobile Month views put a narrow state
  colour strip along the top of every neutral day cell, retain a labelled legend and recalculate
  as the user moves through months. Phones keep a compact seven-column month overview instead of
  a long status list. Week/day/agenda retain detailed status badges; setup and one-day changes
  use shared bottom sheets and large touch targets.
- Database migration required:
  `scheduling.0002_rotatingschedule_rotatingscheduleexception`.
- Validation: **624 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.19 — Household-launch mobile experience

### 0.19.3 — 2026-08-09
- **Maintenance-to-finance round trip** — a Homestead maintenance task can now create or update
  its one Solace bill through the event boundary. The task keeps the practical details; Solace
  keeps amount, schedule and payment history. Finance permission, password re-auth and audit still
  apply, and repeat requests update rather than duplicate the linked bill.
- **Calendar stays single-entry** — once maintenance gains a Solace cost, its Homestead calendar
  mirror is removed and the protected Solace financial event remains authoritative.
- **Visible cross-node journeys** — linked maintenance, insurance and household-cost badges open
  the matching filtered Solace bill view. Synced Calendar event details now offer an “Open the
  source record” route for Atlas, Pets, Education, Homestead, Solace and Meridian.
- **Touch and desktop polish** — hover-reveal controls remain visible on coarse-pointer tablets
  and touch laptops, while the dense Solace and Education workspaces use more available width on
  large desktop screens.
- No additional database migration beyond `homestead.0004` from v0.19.2.
- Validation: **613 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

### 0.19.2 — 2026-08-09
- **Enter home bills once** — Solace bills can now be organised as Homestead home insurance,
  rates/services or paid maintenance at creation time. Existing Solace bills can be handed off
  from Edit without retyping their name, provider, amount, due date or recurrence.
- **One editing owner** — after handoff, Homestead owns the descriptive home record and Solace
  owns payment state/history. Direct Solace edits and deletion are blocked for linked bills;
  Homestead changes continue to update the same bill through the event boundary.
- **No duplicate schedule row** — linked maintenance appears in Homestead but retains only its
  protected Solace financial Calendar event. The Homestead task stores a lightweight bill
  reference, matching policies and household costs.
- **Phone-first finance forms** — the Solace bill form now uses a clean responsive grid, explains
  the Homestead destination in context, and linked cards deep-link to the exact Homestead
  section. Homestead finance cards stack actions into full touch targets on narrow screens.
- **Direct desktop Hub arranging** — while Tune mode is open, cards can be dragged by a visible
  grip on the live Hub or in the configuration list. Mobile retains the accessible arrow controls.
- **Fast reorder persistence** — arrow and drag moves update optimistically and save the full
  order through one atomic batch request, replacing the previous sequential request per widget.
- Database migration required: `homestead.0004_maintenancetask_solace_bill_ref`.
- Validation: **609 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

### 0.19.1 — 2026-08-04
- **Usable dense workspaces on phones** — Solace, Homestead and Education replace their long
  scrolling tab strips with a clear section picker on narrow screens. Solace's bill, bucket,
  subscription, purchase and payday forms now stay collapsed until requested, and its legacy
  double card padding has been removed.
- **Touch actions stay visible** — edit/delete controls that previously depended on mouse hover
  remain available on phones. Homestead maintenance rows stack their content and actions cleanly,
  retain a prominent Done button, and shared fields no longer overflow narrow native date inputs.
- **Search now completes the journey** — Atlas, Pets, Education and Homestead results link to the
  relevant workspace or Calendar date. Shared search controls add a recognisable search cue and
  one-tap clear action; Atlas's new-list form is collapsed until needed.
- **Modal polish** — opening the mobile More sheet now locks the page behind it, preventing the
  disorienting background scroll common on phones.
- **Household countdown** — admins can enable a small Countdown card from Tune my Hub, give it a
  name and target date, and show the whole household the days remaining. It handles today and
  elapsed dates and can be hidden, resized or reordered like other Hub widgets.
- Database migration required: `hub.0013_seed_countdown_widget` (catalogue seed only).
- Validation: **599 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

### 0.19.0 — 2026-08-04
- **Friendlier phone navigation** — the mobile shell now uses the member's avatar, a calmer top
  bar, safe-area-aware bottom navigation and clearer active states. New browsers default to the
  four most useful adult household destinations (Home, Calendar, Atlas and Homestead when
  enabled), while the existing bottom-bar editor still lets each person choose their own four.
- **A useful mobile Home** — the Hub adds a phone-only everyday launchpad for the family calendar,
  lists/notes, home and pets. Copy, sign-in and empty states are warmer, profile/avatar editing is
  available from the phone menu, and the global create sheet uses plain-language choices with a
  direct Home plan action.
- **Less cramped daily work** — shared cards, page headings, tabs and bottom-sheet modals use
  phone-appropriate spacing; long tab bars automatically keep the selected tab visible. Calendar
  Month becomes a readable event list on phones, Solace Schedule defaults to List on phones, and
  notification cards now open their linked record.
- **Optional Solace password prompt** — admins can turn “Ask for a password when opening Solace”
  off in Manage → Solace settings. The secure default remains on. Turning it off removes the
  extra re-authentication gate for Solace APIs while preserving `solace.*` role permissions and
  the existing access audit trail.
- No database migration is required for this release.
- Validation: **597 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.18 — Homestead room and area planning

### 0.18.0 — 2026-08-04
- **Linked room/area workspace** — Homestead now has a Rooms & areas overview where every space
  is a link to its own stable page. Rooms carry type, description, icon, colour, ordering and
  reserved floor-plan metadata so a future clickable map can target the same routes.
- **One plan for everything in a room** — dedicated room pages track purchases, maintenance,
  renovations and upgrades with status, priority, assignee, quantity, estimated unit cost,
  optional actual total cost, reference link and notes.
- **Useful lifecycle and totals** — active work is grouped by type; completed and archived items
  remain visible and can be reopened/restored. Room and whole-house summaries show remaining
  estimates, completed cost (actual where supplied, estimate fallback) and overall cost, with
  archived ideas deliberately excluded.
- **Permission-aware APIs and search** — layered CRUD APIs use the existing `homestead.*`
  permissions and central record visibility rules. Room and plan-item results are searchable
  both inside Homestead and through global search, deep-linking to the room page.
- Database migration required: `homestead.0003_roomarea_roomplanitem`.
- Validation: **593 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.17 — Security maturation: protected attachments

### 0.17.0 — 2026-08-04
- **Shared protected attachment service** — added the canonical D11 attachment model and
  `/api/v1/attachments/` upload/list/download/delete API with household ownership, linked
  node/record metadata, randomized storage names, SHA-256 checksums, upload limits, soft deletion
  and frontend client/types for node adoption.
- **Central record policy** — the permission resolver can now enforce record visibility,
  sensitivity, child/kiosk denial and current re-auth state. Attachment lists hide locked
  metadata; downloads and deletion re-check the record rather than trusting client-side state.
- **Sensitive download audit** — every financial, health, document, private or explicitly
  sensitive attachment download creates an immutable `sensitive_attachment_downloaded` audit
  entry. Regular members may remove only their own uploads; managers/admins can manage all.
- **No public upload bypass** — Django no longer exposes `MEDIA_ROOT` through `/media/`; files
  are streamed only through permission-checked API endpoints. Existing Education assessment
  files now use their own visibility-checked download route, and private assessment detail,
  note and file lookups were tightened against direct-ID access.
- **Actually short-lived re-auth** — password elevation now records a grant timestamp, expires
  after five minutes, removes expired state and rejects permanent boolean flags left by older
  sessions.
- Database migrations required: `attachments.0001_initial` and
  `permissions.0020_seed_attachment_permissions`.
- Validation: **581 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.16 — Solace cash-flow forecast and deep parity

### 0.16.0 — 2026-07-30
- **Bills-account forecast** — a protected 3–24 month cash-flow forecast starts from the latest
  manual balance, adds expected Bills-bucket transfers, subtracts included bills and active
  subscriptions, and exposes the full dated running-balance trail. It reports the lowest
  projected balance, first risk date, required opening balance, bills-only surplus, shortfall,
  and the amount withdrawable while retaining the configured safety buffer.
- **Bill lifecycle depth** — recurring bills now preserve standalone autopay and optional
  stop-after metadata, expose 12 upcoming and 12 historical occurrences, support six-monthly
  entry, category/status sorting and filtering, and let edits refresh future unpaid or all
  budget-year unpaid occurrences while always preserving paid history.
- **Payday workflow parity** — Pay plan and Checklist can navigate current/next cycles. Generated
  checklists now include confirm-income, transfer, review-due-bills and record-balance steps.
  Income cards distinguish the known recurrence anchor from the calculated upcoming payday.
- **Management and reporting parity** — purchase cards have capped quick-add saving; category
  reports include active/set-aside filters and weekly, fortnightly, monthly and yearly totals;
  finance health checks cover fallback categories, remainder rules, percentage ranges and
  missing Bills buckets.
- **Cutover confidence** — the legacy importer preserves/enriches stop dates and autopay, and
  read-only `import_solace --verify` performs natural-key and financially significant field
  comparison before retirement of the standalone app.
- Database migration required: `solace.0007_bill_end_date_bill_is_autopay`.
- Validation: **560 backend tests**, frontend TypeScript check and production build clean; no
  migration drift.

---

## 0.15 — Solace standalone parity

### 0.15.0 — 2026-07-29
- **Pay-cycle closeout and projections** — added current/next cycle navigation, close/reopen
  reconciliation, checklist progress, manual account-balance history and projected balances
  after unpaid bills.
- **Finance health and planning depth** — actionable setup/overdue/balance checks, configurable
  cycle anchor and payday-boundary handling, required fortnightly set-aside, category summaries,
  coverage and shortfall reporting. A configured cycle anchor is authoritative even after
  income sources have been added.
- **Complete management workflows** — responsive create/edit/pause/status/delete flows for
  purchases, income, buckets and subscriptions; custom bill/purchase categories; checklist
  hiding/restoration; currency, buffer, budget-year, help and reminder settings.
- **Cutover tooling** — CSV exports, a readable multi-sheet XLSX backup, preview/confirm/cancel
  bill imports, generic finance-safe scheduled reminders, and full-state legacy migration for
  settings, categories, recurring bills and occurrence history, income, purchases, buckets,
  balances, checklist preferences and closeouts. Legacy subscription-category recurring
  payments remain Bills so their occurrence and set-aside history stays intact. A read-only
  `import_solace --verify` mode reports missing or drifted imported values before retirement.
- **Performance** — the Solace workspace now loads through one consolidated bootstrap request.
- Database migrations required: `solace.0005` and `solace.0006`. The backend image must be
  rebuilt so the new `openpyxl` dependency is installed.

---

## 0.14 — Solace recurring bill schedule

### 0.14.0 — 2026-07-29
- **Correct recurring bill lifecycle** — bills remain recurrence definitions while independent
  `BillOccurrence` rows carry each due date's upcoming/paid/skipped state. Paying one recurring
  occurrence no longer permanently pays the whole bill or removes its recurring Calendar mirror.
  One-off bills retain their existing paid/Undo behaviour.
- **Month-end-safe generation** — weekly, fortnightly, monthly, quarterly, six-monthly and yearly
  schedules materialise idempotently. Monthly rules clamp dates such as the 31st to the end of a
  short month without drifting future occurrences away from the intended day.
- **Native Schedule screen** — Solace now combines bill occurrences and expected income in a
  previous/current/next monthly calendar or action-oriented list. It shows bill, paid, unpaid,
  skipped and income totals and supports Paid, Mark unpaid, Skip and Restore actions.
- **Bill management parity** — Bills can be created, edited, paused, deleted and included/excluded
  from set-aside calculations on the responsive web screen. Cards show annualised and fortnightly
  cost; the page summarizes active annual cost, fortnightly set-aside and category count.
- **Hub and import completion** — the three existing Solace Hub widgets now have working finance
  renderers. Rerunning `import_solace` imports legacy bill-occurrence dates, amounts and statuses
  idempotently in addition to the previously supported records.
- Added `docs/SOLACE_PARITY_CHECKLIST.md` as the live standalone-to-native gap tracker.
- Database migration required: `solace.0004_bill_occurrences`.

---

## 0.13 — Solace pay-cycle planning

### 0.13.0 — 2026-07-29
- **Native pay-cycle planner** — restored the standalone Solace app's core household question:
  how much each income source should transfer into each bucket this fortnight. The protected
  plan groups recurring paydays in the current 14-day cycle, applies percentage rules per income,
  splits fixed household amounts proportionally, rounds transfers, caps them to remaining pay,
  and shows household plus per-income totals.
- **Structured bucket rules** — buckets now store allocation method/value, rounding increment,
  active state, order and remaining-pay protection instead of burying legacy rules in notes.
  Rules can be created and edited from Solace. Paydays can be paused without deleting them or
  leaving stale Calendar entries.
- **Payday checklist generation** — one action turns the calculated bucket totals into
  cycle-specific checklist items. Generation is idempotent and refreshes amounts without
  resetting completed items; the UI defaults to permanent items plus the latest generated cycle.
- **Safe legacy enrichment** — rerunning the idempotent `import_solace` command enriches
  previously imported buckets whose structured allocation value is still zero. New imports
  preserve legacy percentages, fixed amounts, rounding, caps, order and checklist cycle keys.
- Every planner/checklist request remains permission-controlled, password re-authenticated and
  audited. Four new regression tests cover calculations, idempotence, inactive income and
  re-authentication.
- Database migration required: `solace.0003_budget_planner`.

---

## 0.12 — Daily-use experience

### 0.12.0 — 2026-07-29
- **Navigation and findability** — the app shell now shows the current surface, provides
  global **Search** (`Ctrl/⌘ K`) and **Create** actions, supports a user-customisable mobile
  bottom bar, restores scroll position on browser Back, and keeps node tabs in the URL so
  refreshes and deep links retain context.
- **Permission-aware global search** — implemented the canonical `/api/v1/search/?q=` endpoint
  across Calendar and every enabled/permitted node. Results are normalized and deep-linked;
  Solace is reported as locked until password re-authentication and is never searched or leaked
  while locked. Search uses one request instead of fan-out from the browser.
- **Response time** — route-level lazy loading reduced the initial production bundle from about
  543 KB to 245 KB (gzip 137 KB to 75 KB). Shared People/Users/Nodes/Household requests are
  deduplicated and briefly cached with auth-boundary invalidation. API responses expose
  `Server-Timing`, with calls over 500 ms logged for diagnosis.
- **Reliability** — resetting the currently logged-in admin's password now refreshes Django's
  session authentication hash, so Users no longer blanks and the new password immediately
  unlocks Solace. Expired sessions are handled centrally; network, offline, loading, retry and
  empty states are visible instead of silently becoming empty data.
- **Responsive/accessibility pass** — consistent headers on Hub/admin surfaces, mobile
  bottom-sheet dialogs, focus trapping/restoration, keyboard-operable tabs, stronger focus
  rings, coarse-pointer touch targets and reduced-motion support.
- **Faster daily actions** — universal quick-create deep-links to working forms; Atlas
  completion and Solace checklist/bill actions update optimistically; marking a bill paid
  offers Undo. Hub and global-search results deep-link to the relevant surface/tab.
- No database migration is required for this release.

---

## 0.11 — Solace node

### 0.11.3 — 2026-07-28
- **Recurring-completion deployment fix** — declared `python-dateutil` as a backend runtime
  dependency. Pets flea/worming/treatment completion and Homestead recurring maintenance both
  use its RRULE parser; local development had the package installed but the Docker image did not,
  causing a `ModuleNotFoundError` when marking a recurring treatment done.

### 0.11.2 — 2026-07-28
- **Homestead costs & cover** — added protected insurance policies (provider, policy number,
  premiums, renewal, standard/additional excesses, cover summary and claims links) and recurring
  home costs for rates, water, gas, electricity, mortgage/rent, strata, waste and internet.
- Active policies/costs mirror one linked Solace bill through the signal boundary (D4). Updates
  stay idempotent; deactivation/deletion removes the mirror. Financial Calendar events remain
  Solace-owned and retain financial sensitivity/re-auth filtering.
- New six-tab Homestead UI with password-protected Costs & cover, annualised summary, protected
  search, CRUD and sync status. Touchscreen edit/delete actions are now visible, form Cancel
  buttons no longer submit accidentally, and detail queries enforce row visibility.

### 0.11.1 — 2026-07-21
- **Solace legacy importer** — added `python manage.py import_solace --sqlite-db ... --dry-run`
  for the standalone Project Solace SQLite database at `/home/moose/Documents/project-solace`.
  The importer is dry-runnable/idempotent, reads the legacy tables directly, and maps recurring
  bills, subscription-category recurring bills, active income sources/paydays, planned purchases,
  buckets and the latest payday-checklist cycle into native Solace. Recurrence becomes RRULE
  (`recurrence_rule`); dated records use the existing Solace services so Calendar sync stays on
  the D7 helper. Latest-cycle checklist items preserve the legacy cycle/key in notes.
- Import tests cover dry-run rollback, idempotence, subscription mapping and latest-cycle
  checklist import.

### 0.11.0 — 2026-07-21
- **New node: Solace** — native household finance shell (Node Spec 22, decisions **D13/D14**).
  Backend `apps/solace`: bills, paydays, planned purchases, budget buckets/set-asides,
  subscriptions, and payday checklist items. All rows default to `visibility="sensitive"` and
  `sensitivity="financial"`. Dated records sync to the shared Calendar via the scheduling helper
  only: bills, paydays, subscriptions and planned purchases carry `calendar_event_id` and RRULE
  where relevant.
- **Finance safety pass**: Solace permissions are admin-only by default; every Solace API route
  requires password re-auth and audits `sensitive_node_accessed`. Solace is configured as
  disabled by default, kiosk-off, and `requires_reauthentication=True`. Shared Calendar queries
  now suppress sensitive/financial events unless the session is re-authed; Solace Hub widgets
  return no content unless the session is unlocked and the user has `solace.view`.
- Hub widgets: `solace_bills_due`, `solace_subscriptions`, `solace_planned_purchases`
  (web-only, source-node gated).
- Frontend: `/solace` route (node-gated) with password unlock, overview cards, search, and tabs
  for Bills, Buckets, Subscriptions, Purchases, Paydays and Checklist. App version bumped to
  `v0.11.0`.
- **Still to do before full cutover:** inspect the legacy Solace data/schema, build the dry-run
  idempotent importer in `scripts/`, richer edit/delete affordances in the UI, notifications,
  attachments, and live household retirement of the standalone app.

---

## 0.10 — Homestead node

### 0.10.0 — 2026-07-21
- **New node: Homestead** — the household's home/property hub (Node Spec 25, decision **D21**).
  Built for a new home purchase; folds the *home* scope of the planned Assets node into one warm
  surface. Backend `apps/homestead`: `Property` (record + emergency info — water stopcock, gas
  shut-off, consumer unit, boiler), `MaintenanceTask` (recurring/one-off upkeep + renewals;
  `next_due_at` source of truth; RRULE; **mark done → advances to next occurrence**; Calendar sync,
  D7/D8), `Appliance` (brand/model/serial, room, **warranty countdown**, manual link), 
  `ServiceProvider` (trades directory), `Improvement` (status/priority/target-date; dormant
  `project_ref` link to the future Projects node). No money fields — those come from Solace later.
  Full layered app + FTS `search_homestead` + `homestead.*` permissions (perms `0018`) + three Hub
  widgets `homestead_maintenance`/`homestead_warranties`/`homestead_improvements` (hub `0011`) +
  publish-only signals + node catalogue (nodes `0005`, disabled by default). 28 tests.
- **Aggregating-hub design**: Homestead is built to later surface Solace bills/rates and Projects
  renovations (read-only, deep-linked) via the events bus — never importing another node's models
  (D4). The Overview flags this as "coming soon".
- Frontend: `/homestead` route (node-gated) + nav/accent; **five tabs** — Overview (property card +
  emergency info + at-a-glance due/warranties/improvements + future-hub note), Maintenance (due
  badges, one-tap Done, recurrence picker), Appliances (warranty-countdown cards), Improvements
  (grouped by status), Contacts (trades directory) — plus Homestead-wide search and Hub renderers.

## 0.9 — Pets node

### 0.9.2 — 2026-07-21
- **Calendar + Atlas web/mobile UX pass** (owner: the daily-use surfaces felt clunky on phone
  and laptop). Functionality unchanged — this is a feel/entry pass.
  - **Calendar**: the crowded filter row (person, my-events, source layers, week-start, 12/24h,
    set-as-default) collapses into a single **Filter** popover with an active-filter count badge;
    bigger nav (‹ Today ›) targets. New **inline quick-add** bar on Day and Agenda that parses a
    time from the text (e.g. "Dentist 3pm") so the common case takes one line. The event modal now
    shows just **Title + Start**, with end/location/assignee/colour/visibility tucked under
    **"More options"** (auto-expanded when editing an event that already uses them). Week-view days
    are shorter on mobile and tappable to add.
  - **Atlas**: a unified **quick-capture** bar on top routes a line of text into a **To-do**
    (into a chosen list), **Note**, or **Reminder** and jumps you to where it landed. List add-row
    no longer wraps awkwardly on mobile (stacks input, then who + Add); the reminder form collapses
    behind **"+ New reminder"** like notes; list cards show a "N to do" count.
  - Shared: new `Popover` component and a small `parseQuickEvent` time parser.

### 0.9.1 — 2026-07-20
- **Layout polish**: the sidebar header and the top bar are now the same height so their
  bottom borders line up across every page. **Books** page cleanups — native selects get
  room for their dropdown arrow (the "Backlog" label was being clipped), the book-tile
  controls are stacked so nothing is cramped, and the shelf toggle is grouped with the shelf
  tabs instead of floating out to the right.

### 0.9.0 — 2026-07-20
- **New node: Pets** — pet care tracking (Node Spec 13). Backend `apps/pets`: `Pet` profiles
  (species/breed/photo, vet + microchip + insurance + food notes), `PetTreatment`
  (flea/worming/vaccination/medication/grooming, `next_due_at` source of truth, RRULE
  recurrence) and `PetAppointment` (vet visits) — both sync to the shared Calendar (D7).
  Marking a treatment done stamps `last_done_at` and advances `next_due_at` to the next RRULE
  occurrence (D8); non-recurring ones clear the reminder. Full layered app + FTS search +
  `pets.*` permissions + two Hub widgets (reminders due, upcoming appointments) + domain
  signals. Frontend: `/pets` route + nav stack, Pets tab (profile cards with inline treatments
  & appointments, add/edit/delete), Reminders tab (all due, one-tap Done) and Appointments tab,
  pet-wide search, and Hub renderers. Disabled by default — enable it in Settings.
- **Milestone 3 complete** — Education, Home Wiki and Pets all shipped.

## 0.8 — Home Wiki node

### 0.8.0 — 2026-07-20
- **New node: Home Wiki** — the household knowledge base for persistent reference info (WiFi,
  bin night, emergency contacts, appliance how-tos). Backend `apps/home_wiki`: `WikiCategory`
  (admin-manageable, 12 seeded defaults) + `WikiPage` (title/body, category, comma tags,
  favourite/emergency/kiosk-safe flags, visibility + sensitivity). Full layered app + FTS
  search + `homewiki.*` permissions + three Hub widgets (favourites, emergency, recently
  updated) + domain signals. Frontend: `/wiki` route + nav stack, Pages tab (filter by
  All/Favourites/Emergency + category, create/edit/delete, expandable bodies, pin favourites)
  and Categories tab (add/hide/delete for admins), wiki-wide search, and Hub renderers.
  Disabled by default — enable it in Settings.

## 0.7 — Node fleshing-out & shared UX parity

### 0.7.8 — 2026-07-20
- **Meridian import**: the `import_meridian` command now imports **legacy task-completion
  history** (`task_completions`) into `MeridianTaskCompletion` — status, submitted/reviewed
  timestamps, rejection reason, review note and evidence path are preserved. Idempotent
  (deduped by task + person + submitted time) and dry-runnable like the rest of the importer.

### 0.7.7 — 2026-07-20
- **Meridian** form inputs across all the large sub-tabs (Tasks, Shop, Routines, Goals &
  Wishlist, Reports & Settings) now use the shared field styling instead of hand-rolled input
  classes — one visual language, matching every other node, with larger touch targets.

### 0.7.6 — 2026-07-20
- **Education** gains an **Events** surface — excursions, school events, term start/end, exam
  blocks, holidays and milestones. Events sync to the shared Calendar (all-day by default) and
  can be tied to a course or institution and assigned to a person. New **Events** tab on the
  Education page, an **education_events** Hub widget (upcoming events), and events are now
  included in Education search.
- **Education notifications & signals**: creating an assignment or event now notifies the
  assigned person (when it isn't their own), and the node publishes its domain signals
  (`assessment_created`, `assessment_completed`, `class_session_created`, `school_event_created`)
  onto the event bus.
- **Education layout**: the page now uses the wider desktop container (matching the other
  nodes) with three-column course/institution grids on large screens.

### 0.7.5 — 2026-07-19
- **Books**: the add-book form now suggests existing books as you type the title, so you can
  reuse a record instead of creating a duplicate; inputs and header moved onto the shared kit.

### 0.7.4 — 2026-07-19
- **Meridian** tasks gain a **weekly recurrence** picker (choose the weekdays a repeatable
  task re-arms on) in both the create and edit forms — the backend already stored/honoured
  the RRULE, but there was no way to set it. Repeating tasks now show a "↻ days" badge.
- _Remaining Meridian parity (follow-up): photo evidence on completions and importing legacy
  completion history._

### 0.7.3 — 2026-07-19
- **Education** gains an **Institutions** management tab (add / edit / delete schools and
  universities) and an **education-wide search box** (courses, assignments, classes) wired
  to the existing FTS endpoint.
- _Remaining Education parity (follow-up): a dedicated Education Events model (excursions /
  term dates / school events), plus notifications and outbound signals._

### 0.7.2 — 2026-07-19
- **Atlas** gains a full **Notes** surface (browse / create / inline edit / delete, with
  household-or-private visibility) — previously notes only appeared in search.
- **Create a list of any type** (to-do, grocery, shopping, checklist, general) from a picker
  instead of always making a to-do list; lists now lay out in a responsive two-column grid.
- Reminders form and empty states moved onto the shared kit.

### 0.7.1 — 2026-07-19
- **Calendar** UX pass: event modal rebuilt on the shared Modal/Field kit; per-source
  **layer toggles** and a **My events** filter; **household calendar defaults** (default
  view, week-start, time format) an admin can set, with each user's own choices still
  taking precedence; calmer empty states. New migration `core/0004`.

### 0.7.0 — 2026-07-19
- **Shared UI kit**: new reusable primitives (`Field`/`Input`/`Textarea`/`Select`, `Tabs`,
  `Modal`, `EmptyState`, `Badge`, `PageHeader`) so every node shares one visual language.
  Adopted across the Meridian, Atlas and Education tab bars, headers and inputs.
- **Hub**: three new widgets — **Quick add** (add a reminder or note from the Hub),
  **Notifications** summary (unread count + recent, web-only), and an opt-in ambient
  **Thought for the day**. New seed migration `hub/0007`.

---

## 0.6 — Books Node

### 0.6.3 — 2026-07-17
- Books can now be edited inline from any individual shelf category.
- Club book cards also expose the same edit action because club entries share the underlying book record.
- Editable fields: title, author, pages, genre, ISBN, and description.

### 0.6.2 — 2026-07-17
- Global web layout widened from a narrow centered column to a responsive full workspace (`max-width: 1600px`) so nodes use desktop real estate properly.
- Books page now uses wider desktop grids with side panels for shelf counts, club items, and up-next, while keeping stacked mobile layout.
- Added the Books accent colour to shared UI tokens.

### 0.6.1 — 2026-07-17
- Books page UX changed to tab navigation: top-level Individual / Book club tabs, then Backlog / Reading / Read tabs inside each view.
- Added a top add-book control that selects the destination shelf when adding.
- Each book now has a shelf dropdown that moves it between Backlog, Reading and Read.
- Personal backlog books can be added directly to a selected book club.

### 0.6.0 — 2026-07-17
- New Books node: personal shelves for backlog, currently reading, and history.
- Book details include title, author, pages, genre, ISBN, description, and cover URL.
- One user rating/note per book, reused across personal shelves and book club history.
- Book clubs: create/edit club name and colour, add/remove HomeStack users, and collaboratively add/remove/reorder books.
- Club books track backlog, currently reading, and history; history shows member ratings and club average.
- Up-next queue for clubs sits separately from the full backlog and can be ordered independently.
- Club books also appear on a member's personal shelves, highlighted by club colour, with a filter to hide club items.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (books `0001`, nodes `0004`, permissions `0015`).

---

## 0.5 — Education Node (M3)

### 0.5.2 — 2026-07-17
- User colour is now editable in the Users admin page (added colour picker to edit form; was previously read-only).
- Person name sync fix: linking an existing person to a user account now copies the user's display name to the person (previously only colour was copied, leaving persons stuck with their original name e.g. "admin").
- Education academic profile: institution field replaced with a free-text input + datalist autocomplete. Typing a new institution name creates it automatically on save; existing institutions still autocomplete.
- Settings page expanded: Household card (name + timezone), Stacks toggles (read-only for non-managers), Family colour (unchanged), and a new Meridian card (points label + group goals / wishlist requests / auto-end streaks toggles) — Meridian card only shows when the stack is enabled.

### 0.5.1 — 2026-07-17
- Assessment notes: per-assessment text notes (add, edit, delete) inline on the Assignments tab.
- Assessment files: file upload/download on each assessment (criteria PDFs, reference docs); stored in `MEDIA_ROOT/education/assessments/<id>/`; served via Django in dev, Docker `media_data` volume in prod.
- Auto-assignee: assignment form now pre-selects the logged-in user (fixed async `useEffect` sync).
- User profile self-edit: `PATCH /api/v1/auth/me/` lets any user change their own display name, colour, avatar, PIN, or password without admin access. Accessible via clicking the user panel in the sidebar.
- Display name → Person sync: renaming an account now also renames the linked Person record.
- Academic profile: per-person enrolment profile (institution, programme, credits required, graduation year, notes). GET auto-creates a blank profile so the tab never 404s.
- Course credit tracking: `credit_value` and `is_completed` fields on courses; profile view shows a live credit progress bar (current/required/percentage).
- Module bucketing: profile page groups courses into Current / Upcoming / Past based on start/end dates and completion state.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (education `0003` + `0004`).

### 0.5.0 — 2026-07-14
- Education node: institutions, courses (with colour, teacher, dates), assessments (due dates sync to Calendar via D7 CalendarSyncMixin), class sessions (weekly timetable via RRULE).
- Two Hub widgets: upcoming assessments and today's timetable.
- `EducationPage`: Assignments tab, Courses tab, Timetable tab — mobile-first responsive layout.
- `education.*` permissions seeded; `education.delete` is admin/manager only.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (permissions `0014`, hub `0006`, education `0001`).

---

## 0.4 — Meridian Cockpit Revisit

### 0.4.0 — 2026-07-10
- Task completion model (`MeridianTaskCompletion`): per-person submission/approve/reject history with review notes.
- Adult Meridian Overview tab: pending approvals, balances, recent activity.
- Task management table: filters, inline edit, hide/archive/delete, completion history.
- Shop/Rewards management: metrics, reward table with inline edit, stock management, pending request queue.
- Reports/history cockpit: completion history, points ledger, badge catalogue, leaderboard.
- Category management UI in Settings tab.
- Reward-category linking: `MeridianReward.category` FK + filter/display in shop.
- Allowance config UI/API: per-person weekly allowance amount and weekday, togglable, manager-only PATCH.

---

## 0.3 — Core Surfaces: Hub, Atlas, Calendar (M2.5)

### 0.3.0 — 2026-06-25
- Hub widget config: per-household enable/disable/order/size, per-user hide/reorder; "Customise" panel on the Hub page.
- Ambient clock Hub widget (kiosk-safe, client-side).
- Atlas FTS: Postgres `SearchVector`/`SearchQuery` in prod, `icontains` fallback on SQLite; `GET /atlas/search/?q=`.
- Atlas list items gain `due_at` and `quantity`; due-date badges and quantity prefix in the UI.
- Calendar core: month/week/day/agenda views; per-person colour coding + legend; `start`/`end`/`node`/`person` filter params.
- `CalendarPeek` popover in the shell header (next events, quick-add).
- Calendar event create/edit/delete modal; synced events read-only with "edit in node" note.
- `calendar_upcoming` Hub widget (web + kiosk).
- Kiosk restyle: warm paper tokens, kiosk Calendar surface (month/week/day/agenda).
- Web login user-tile flow (avatar picker → PIN); emoji account pictures stored in `User.avatar`.
- Enter/Exit kiosk buttons; hardware-keyboard PIN entry; admin-only price fields in shop/wishlist/goals.

---

## 0.2 — Native Meridian Full Port (M2) + User Management

### 0.2.0 — 2026-06-25
- User management admin page: create/edit/deactivate users, link to Person, role management, PIN/password reset, avatar emoji picker.
- Meridian full port: tasks (completion scope, hot bonus, archive, recurring), reward shop (stock, daily limits, cart/checkout), routines + streaks, group goals, wishlist (request/approve/fund/fulfill), points ledger (typed transactions, balance vs lifetime-earned), reward reservations/refunds.
- Cross-node achievements/badges: 15 seeded badges, `PersonBadge`, `AchievementCounter`; awarded via events bus (no Meridian imports).
- Notifications: `Notification` model, `GET /notifications/`, unread count; wired into Meridian approvals and badge awards.
- Scheduled management command (`meridian_run_scheduled`): weekly allowances, perfect-month routine badges.
- Meridian settings: `points_label`, `group_goals_enabled`, `wishlist_requests_enabled`, `auto_end_streaks`; `GET/PATCH /meridian/settings/`.
- Reports/leaderboard API: `GET /meridian/reports/`.
- Full Meridian data import command (`import_meridian`): categories, points ledger, routines, goals, wishlist, badges, allowances — idempotent by natural keys.
- Full web frontend: Tasks board, Shop, Routines, Goals, Wishlist, Leaderboard, Badges, admin Settings panel.
- Full kiosk: tap-to-complete tasks and routines (celebration), reward shop, goals/wishlist quick-contribute, my-badges strip.
- CSRF fix: `@ensure_csrf_cookie` on `GET /auth/me/` + client reads `csrftoken` cookie for unsafe requests.

---

## 0.1 — Walking Skeleton (M1)

### 0.1.1 — 2026-06-24
- Nodes registry: `Node` catalogue (12 seeded), `HouseholdNode` (enable/disable), `NodeSetting`; `GET /nodes/`, `POST /nodes/<key>/enable|disable/`, `PATCH /nodes/<key>/settings/`.
- `AuditLog` (append-only): `log_audit()` helper; `GET /audit-logs/`; login events wired.
- `CalendarEvent` model + `CalendarSyncMixin`; `sync_event_for`/`delete_event_for` helpers (D7 — nodes never write CalendarEvent directly); full Calendar CRUD API.
- Atlas node: `AtlasNote`, `AtlasList`, `AtlasListItem`, `AtlasReminder` (calendar sync); full CRUD + visibility filter; `events` signal bus (D4).
- Hub node: `HubWidget`, `HouseholdHubWidget`, `UserHubWidget`; `GET /hub/` and `GET /hub/kiosk/`; Atlas todo + reminder widgets seeded.
- Kiosk frontend: state machine (ambient → avatar select → PIN → dashboard → idle timeout); Avatar + PIN components; kiosk users endpoint (`AllowAny`).
- Backups: `Backup` model; `create_backup` (pg_dump + media tar, checksum, audit), `restore_backup`; streaming download; `docs/restore.md`.
- Web frontend: `LoginPage` (avatar tiles → PIN); `AppShell` (sidebar + mobile bottom nav, dark mode); `HubPage`, `AtlasPage` (lists/reminders), `CalendarPage` (grouped upcoming events).
- `HomeStackPermission.for_resource()` DRF factory; `permission_action` view attribute for method overrides.

### 0.1.0 — 2026-06-23
- Repo scaffold: `backend/ frontend/ docs/ docker/ scripts/ backups/`; `.env.example`; `docker-compose.yml` + `docker-compose.dev.yml` (3 services: postgres, backend, frontend; hot-reload bind mounts; `media_data` + `backup_data` volumes).
- Django project: split settings `config/settings/{base,dev,prod,test}.py`; 14 app skeletons (`core accounts people permissions nodes hub scheduling notifications attachments audit search backups events atlas`); DRF + argon2-cffi.
- `core.Household` (single-row tenant anchor) + idempotent seed migration; `HouseholdBaseModel` (abstract: household FK, soft-delete, created/updated-by-user); `HouseholdManager`.
- `accounts.User` (AbstractBaseUser + HouseholdBaseModel): `display_name`, `username`, `email`, `avatar`, `pin_hash`, `role`, `colour`; `PinBackend` + `PasswordBackend`; session auth endpoints (`pin-login`, `password-login`, `logout`, `me`, `reauth`).
- `people.Person` (HouseholdBaseModel): `linked_user` (nullable OneToOne), `display_name`, `preferred_name`, `avatar`, `colour`, `date_of_birth`, `profile_type`; full CRUD API.
- Permission spine: `Permission` catalogue, `Role` (4 system roles), `RolePermission`, `UserPermission` overrides; resolver; `HomeStackPermission` DRF class; 4 `people.*` permissions seeded with default matrix.
- Household settings endpoint: `GET/PATCH /household/`.
