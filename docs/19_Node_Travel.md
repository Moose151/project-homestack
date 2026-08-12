# Node Spec — Travel

> **Status:** shipped and in use as a real HomeStack domain. The initial Trips/To go/booking/cost
> slice shipped in v0.33.0; itinerary/Things to do plus explicit day-trip/multi-day-trip behaviour
> shipped in v0.34.6. Packing and protected travel-document workflows remain future additions.

## 1. Purpose

Travel owns household trip planning from the first "we should go there" idea through a structured
trip, bookings, itinerary/Things to do and trip history.

It answers:

- Where might we go?
- Which trips are actually planned?
- Who is going?
- What still needs booking?
- What will it cost?
- What might we do on each day?

It does not replace Atlas for general lists, Solace for household finance, or shared Attachments for
protected file storage.

## 2. Primary surfaces

Travel has two main entry views:

- **Trips** — active/past plans with planning/booked/travelling/completed-style state as supported
  by the implementation.
- **To go** — lightweight destination ideas that can later be converted into a Trip.

A Trip has a stable detail route and progressively exposes trip overview, bookings/travel & stays,
Things to do/itinerary and related information without forcing every trip to use every feature.

## 3. Trips and trip type

A Trip owns its title/destination, notes, dates, colour, visibility, participants and other current
planning fields.

`trip_type` distinguishes:

- **day trip** — start/end are the same date; save/edit logic keeps them aligned;
- **multi-day trip** — normal start/end range.

The owning Trip remains the source of truth for its dates/status/participants. Its Calendar block is
a projection maintained through D7.

## 4. Participants and surprise visibility

Participants are People. Empty participant selection may represent the whole household according to
the current implementation contract.

A separate surprise/hidden-user control can exclude selected linked Users from a trip/idea that
would otherwise be visible. This is not the same as participant assignment.

The exclusion must be respected consistently across:

- Travel list/detail/direct-ID routes;
- Calendar and Agenda projections;
- Hub;
- Search;
- Notifications;
- Corners/activity.

A hidden User must not recover the destination or other trip details by guessing IDs or opening a
derived record. The creator cannot accidentally exclude themselves where the implementation guards
that case.

## 5. To go / Travel ideas

A lightweight idea can carry the implemented useful subset of destination/title/location/comments,
rough cost/currency, participants, visibility/colour, images, travel/accommodation flags and
surprise exclusions.

**Plan this trip** converts the idea into one Trip while retaining confirmed information and linking
back to the created Trip. Repeating conversion should remain idempotent rather than create duplicate
Trips.

Household-visible idea notifications remain source/permission-aware and should not notify excluded
Users or the creator unnecessarily.

## 6. Images

Trip/idea images use the established Travel/image/shared-attachment/link rules. Remote image failure
must degrade safely rather than break the trip.

Do not scrape destination pages automatically or store copied copyrighted page text merely because
a URL was supplied. Where the shared link-import capability is useful, retain its safe URL/provenance
boundary.

## 7. Bookings and costs

Travel booking/component records can represent the implemented categories such as flights,
accommodation, transport, activities, restaurants or other trip reservations.

Shared concepts include the relevant combination of:

- provider/title;
- planned/booked/cancelled state;
- quoted/actual cost and currency;
- booking reference/notes/link;
- start/end/check-in/out/departure/arrival timing;
- location;
- `book_by` deadline;
- component-specific flight/stay fields.

Costs belong to Travel as **trip planning totals**, not household bank/budget history. Mixed
currencies must not be silently added without a real conversion rule.

Solace may later link budget/set-aside context but remains the finance source of truth.

## 8. Calendar and booking deadlines

The Trip owns its start/end date range and projects one trip block into Calendar where appropriate.
Timed booking components such as flights/stays can create their own source-linked Calendar mirrors
through D7.

An unbooked component with a `book_by` deadline owns that deadline. Calendar/Atlas Agenda/Hub may
project it as one actionable item. Marking the component booked/cancelled resolves/removes future
actionability without deleting the booking history.

Changing participants/visibility/surprise exclusions must update what derived surfaces return; they
must not retain stale visibility.

## 9. Things to do / itinerary — shipped

Travel itinerary is now a first-class shipped Trip-owned feature.

A `TravelItineraryItem` represents something the household may do during the Trip. It includes the
implemented combination of title, location, notes and optional booking/source context.

The key scheduling model is:

- item assigned to a **specific day of the Trip**; or
- item left **unassigned/unscheduled as an "option to do"**.

Dated items project into Calendar through D7 using the Trip's applicable visibility/participant/
surprise rules. Clearing the assigned day removes that Calendar projection.

Do not invent a separate general itinerary calendar. The Travel item remains the source of truth.

If timed itinerary items are added later, extend this model deliberately rather than documenting
time fields as already supported when they are not.

## 10. Packing — future slice

Packing remains a natural Trip-owned checklist because its lifecycle is specific to the trip.

Future packing should support:

- item text/quantity;
- shared or per-Person responsibility;
- packed/unpacked state and completion audit;
- reusable templates only if they reduce real household friction.

General non-trip checklists still belong in Atlas.

## 11. Travel documents — future sensitive slice

Tickets, confirmations, insurance and identity/passport material should use the shared protected
Attachment capability linked to Travel records.

Identity/passport information is sensitive and must not leak through ordinary Search, Hub, kiosk,
Corners or push payloads. A travel-document feature should be built only with an explicit
visibility/re-auth/download policy.

## 12. Hub / Notifications / Corners

Potential/current Travel projections include:

- next trip/countdown;
- booking deadlines/overdue items;
- booked-vs-required progress;
- trip/destination activity visible in Corners;
- trip approaching / booking changed / itinerary reminders.

Notification delivery uses the shared in-app/Web Push preference system. HTTPS is now live; Web
Push implementation is the active cross-cutting workstream. Travel must not create its own phone
notification channel.

Sensitive/surprise trip text is filtered before notification payload generation.

## 13. Events and search

Travel publishes meaningful source events for trip/idea/booking/itinerary changes through D4.
Other domains may react without importing Travel models.

Search covers permitted trip/idea/booking/itinerary content according to current implementation and
must enforce surprise/visibility filtering before snippets are built.

## 14. Data ownership

Exact schema is defined by current Django models/migrations. Travel owns the implemented equivalents
of:

- Trips;
- To-go/ideas;
- participant/hidden-user associations;
- images;
- bookings/components;
- itinerary/Things-to-do items.

Packing records will be added only when that slice is implemented. Attachments remain shared core
records linked to Travel.

## 15. Completion state

The current useful Travel baseline is complete:

- Trips and To go;
- participant/surprise visibility;
- images/notes;
- conditional flight/accommodation and other bookings;
- planning/actual cost roll-ups;
- Calendar and book-by actions;
- Hub/notification/Corner integration;
- day-trip/multi-day-trip behavior;
- Things to do items assigned to a Trip day or left as unscheduled options.

Future work is no longer "build the itinerary". Remaining likely slices are:

1. packing;
2. protected travel documents;
3. optional richer maps/weather/live-flight/external-booking integration only when useful;
4. deeper Solace/Pets/home-care handoffs without duplicating ownership.

## 16. Acceptance invariants

- Trip dates/status/participants have one owning Travel record and correct Calendar projection.
- Day trips cannot drift into a different stored end date.
- Hidden/surprise Users cannot recover trip data through Travel or derived surfaces.
- Booking deadlines appear once and resolve when booked/cancelled.
- Idea conversion is idempotent and retains confirmed information.
- A dated Things-to-do item appears correctly on the selected Trip day; making it an unscheduled
  option removes the Calendar mirror without deleting the itinerary item.
- Travel planning costs do not become a competing financial ledger.
- Protected/sensitive future documents will not be exposed through normal household summaries.