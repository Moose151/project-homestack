# Node Spec — Travel

> Canonical. **Initial useful slice shipped in v0.33.0 (2026-08-11).** Global rules from
> `00_README_and_Changelog.md` apply: household-scoped base models; assignments are People (D12);
> dates sync only through the Calendar helper (D7); cross-node effects use signals (D4); shared
> attachments own uploaded files; reads use central visibility (D10) and Postgres FTS (D9).

## 1. Purpose and shape

Travel plans holidays from the first “we should go there” idea through research, booking, the
trip itself and history. It should feel like Homestead room projects: one calm project page with
summary, participants, images, component rows, costs and completion states, rather than a dense
travel-agent form.

It answers: **Where might we go? What are we planning? What still needs booking? What will it
cost?** It does not replace Atlas for unrelated lists, Solace for household budgeting, or shared
Attachments for file storage.

## 2. Navigation

The node opens with two primary tabs:

- **Trips** — active and past trip plans, grouped by planning/booked/travelling/completed state.
- **To go** — lightweight destination ideas which can later be promoted into a full Trip.

A Trip has a stable detail route and sections for Overview, Travel & stays, Things to do,
Packing/documents and Images. Progressive disclosure hides flight/accommodation forms until their
requirement is enabled.

## 3. Trips

A `Trip` stores title, destination/place, comments/description, start and end dates, timezone,
status (`planning`, `ready_to_book`, `booked`, `travelling`, `completed`, `cancelled`), selected
Calendar colour, visibility and People participants. Empty participants means the whole household;
otherwise several selected People means all of those individuals. A separate **Keep this a
surprise** control can hide a household-visible Trip from selected linked Users. This exclusion is
copied to every owned Calendar entry/deadline and enforced for direct links as well as lists.

Two explicit requirements—**Flights required** and **Accommodation required**—control the setup
checklist and visible sections. They do not imply booked: each required component must have at
least one relevant booking marked booked before the trip can be considered fully booked. Users
may still add transport, activities, restaurants and other reservations independently.

Comments are ordinary editable trip notes in the first slice. A later discussion stream is not
required merely because several people can see a trip.

## 4. Images

Each Trip and To-go idea may have multiple ordered images with caption and optional credit/source.
Support both an external public image URL and an uploaded/cached shared Attachment; never store
image bytes or filesystem paths on Travel records. One image can be selected as the cover. Failed
or blocked remote images degrade to a placeholder without breaking the trip.

The initial implementation does not scrape destination pages automatically. The shared safe-link
service may later preview a public page, but saving a source URL never grants permission to copy
copyrighted text or bypass access controls.

## 5. Flights, accommodation and other bookings

`TravelBooking` types: flight, accommodation, transport, activity, restaurant and other. Shared
fields: title/provider, status (`researching`, `planned`, `booked`, `cancelled`), quoted amount,
currency, booked/paid amount, booking reference, notes, URL, start/end time, timezone, location,
`book_by`, and visibility. Booking reference and sensitive documents remain adult/restricted.

Flight rows additionally support flight number, departure/arrival airport, departure/arrival
time and leg direction; multiple rows naturally support outbound, return and multi-city travel.
Each timed flight creates exactly one node-owned Calendar event and updates/removes it through D7.

Accommodation rows support property/address, check-in/check-out and number of nights. Multiple
stays are allowed. Check-in/out may appear as one stay event or two concise Calendar markers, but
must never create duplicates.

Every component has a **Booked** action/check box. Marking it booked records who/when, retains the
quote, permits an actual booked amount, and resolves its associated booking deadline. Reopening a
component restores the actionable deadline if it is still relevant.

## 6. Cost roll-up

The Trip summary calculates rather than stores:

- quoted total and booked/actual total;
- flights, accommodation, transport, activities and other subtotals;
- booked versus outstanding component count;
- optional amount still expected to book.

Amounts belong to the booking component and are treated as whole-party totals by default; a
component may optionally record quantity/people count and a per-person note. Currency conversion
is deferred—mixed currencies remain visibly separated and are never silently added together.
Solace integration later links a travel budget or purchase plan; Travel must not duplicate bank,
bucket or payment-history logic.

## 7. Calendar and booking state

The Trip owns its all-day start/end Calendar block. Its selected colour is editable from the Trip
screen and is inherited by its flight/stay events unless a booking overrides it. The Calendar
title/status treatment makes **Planning** versus **Booked** visible at a glance (for example a
clear status chip/icon plus the same trip colour); status updates the existing mirror rather than
creating a new event.

Flight departure/arrival times and applicable stay times appear in Calendar. All events are
assigned to the Trip participants and inherit its visibility. Calendar details deep-link to the
Trip or booking source; synced events remain read-only in Calendar.

## 8. Book-by actions, Atlas Agenda and Hub

An unbooked required component may have a `book_by` date. Travel owns that deadline and mirrors it
once into Calendar; Atlas Agenda automatically projects it as an actionable Travel item without
copying a second Atlas record. The action is **Mark booked**, not an unrelated duplicate checkbox.
Booking/cancellation removes it from upcoming work while preserving the booking record and audit
history.

Hub widgets show: next trip/countdown; bookings due soon/overdue; booked-versus-required progress;
and packing progress. “Coming close” uses the user's shared reminder lead-time preference when the
notification work lands, with a sensible node default until then.

## 9. To go

A `TravelIdea` is deliberately lighter than a Trip: destination/title, where it is, comments,
flight/accommodation requirement flags, rough cost/currency, participants (optional), visibility,
colour, selected surprise exclusions and multiple images. It has states active, converted and
archived. Conversion retains both participants and surprise exclusions.

**Plan this trip** opens a preview and transactionally creates one Trip, copies the confirmed
fields/image links and marks the idea converted with `converted_trip_id`. Repeating the action is
idempotent and opens the existing Trip. Research notes are preserved; no fields are silently
discarded.

When a permitted user adds a household-visible idea, other household users receive one bundled,
source-linked in-app notification. The creator is excluded; private ideas notify nobody. Phone
delivery follows shared preferences only after HTTPS/Web Push is available.

## 10. Itinerary, packing and documents

Itinerary items are dated/timed activities with location, notes and optional booking link; dated
items sync through Calendar. Packing is a Trip-owned checklist with shared or per-Person items and
packed state. Uploaded confirmations, tickets, insurance and permitted identity documents use
shared Attachments. Passport/identity material is sensitive and never exposed in ordinary Search,
Hub, kiosk or notification payloads.

## 11. Permissions and social behaviour

`travel.view/create/edit/delete` follows normal node roles. Visibility supports household,
private and restricted records. In addition, Trips and ideas may explicitly exclude selected
linked Users for surprise planning. That exclusion applies even to managers/admins and across
Travel API/UI, Calendar and Agenda list/detail routes, Hub projections, notifications, Search and
Corners; the creator cannot accidentally exclude themselves. Children see only permitted trip
summaries/packing; adult-only references, costs and identity documents stay hidden. Participant
assignment is not itself an ACL: visibility still decides who may read the record.

Notifications: destination idea added; participant assigned; booking deadline approaching/
overdue; booking added/changed; trip approaching; packing incomplete. Avoid noisy per-keystroke
alerts—notify on meaningful saves and bundle related changes.

## 12. Events, search and integrations

Publishes: `travel.idea_created`, `travel.idea_converted`, `travel.trip_created`,
`travel.trip_updated`, `travel.booking_saved`, `travel.booking_booked`,
`travel.booking_deadline_due`, `travel.packing_item_created`, `travel.packing_complete`.
Consumes later: `solace.travel_budget_updated`, `pets.care_required`,
`atlas.list_completed`. Nodes do not import each other's models.

FTS covers trip/idea destinations and comments, providers, airports, accommodation, itinerary,
packing and attachment metadata, always permission-filtered.

## 13. Proposed data model

- `travel_trips` — core plan, status, dates, colour, requirement flags, visibility;
  M2M `participants`, M2M `hidden_from_users`; `calendar_event_id`.
- `travel_ideas` — lightweight To-go entry, requirements/rough cost, conversion link;
  M2M participants and `hidden_from_users`.
- `travel_images` — trip or idea parent, URL or attachment, caption/credit, order, cover flag.
- `travel_bookings` — typed flight/stay/other component, times, quote/actual cost, booked state,
  `book_by`, booking/deadline Calendar references.
- `travel_itinerary_items` — dated activity and optional booking link; Calendar reference.
- `travel_packing_items` — text, quantity, assigned People and packed-by audit fields.

All user-facing records inherit `HouseholdBaseModel`. Use the existing multi-Person assignment
pattern rather than a singular assignee. Avoid polymorphic generic foreign keys for the two image
parents: use explicit nullable Trip/Idea FKs with a constraint that exactly one is set.

## 14. Delivery slices

1. **Trips and To go:** permissions first, models/API/FTS, participants, images, conversion,
   responsive list/detail UI and idea-added in-app notification.
2. **Required bookings and costs:** conditional flight/accommodation sections, multi-leg/stay
   rows, booked controls, quote/actual roll-ups and readiness state.
3. **Calendar, deadlines and Hub:** Trip/flight/stay sync, at-a-glance booked state, book-by
   Agenda actions, notifications and widgets.
4. **Itinerary, packing and documents:** trip-day activities, assigned packing and protected
   attachments. Solace/Pets automation remains a later integration.

## 15. Completion criteria

- Create a household trip, assign several People, select dates/colour, add several images and see
  exactly one correctly coloured planning block in Calendar.
- Require flights and accommodation, add outbound/return flights plus a stay, record quotes,
  mark components booked and see exact category/total/progress figures.
- Flight times appear once in Calendar. Changing trip participants/colour/status updates all
  owned mirrors and visibly distinguishes planning from booked.
- Give an unbooked component a book-by date; Calendar, Atlas Agenda and Hub show one actionable
  deadline, and marking it booked resolves the action without erasing history.
- Add a household-visible To-go idea; other permitted users receive one notification. Convert it
  once into a pre-filled Trip with its notes/images retained.
- Private/restricted trips, costs, references and attachments do not leak through API, Search,
  Calendar, Hub, notifications, Corner or kiosk tests.
- Hide a surprise plan from one selected linked User; it remains available to its creator but is
  absent for the selected User from Travel and Calendar lists and returns 404 through direct
  Travel/Calendar URLs. No destination notification is sent to that User.

## 16. Deferred

Maps/routes, live flight status, external booking APIs, collaborative comments, weather, currency
conversion, travel journal/photo timeline, itinerary export, pet-care automation and deep Solace
budget integration remain later. No external service is required for the first useful release.
