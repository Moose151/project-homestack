# Node Spec — Travel

> Canonical. **Later node** (post-V1). Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Manages trips, holidays, itineraries, bookings, packing and travel preparation in one organised
place, integrating with Calendar, Atlas, Documents, Solace and Pets. Answers: *"What's happening
for this trip, and what do we still need to do?"* Doesn't replace Atlas (generic checklists) or
Solace (financial planning) — it links to them.

## 2. Belongs / does not belong

**Belongs:** trips, itineraries, flights, accommodation, bookings, packing lists, travel
documents, travel tasks, countdowns, trip notes.
**Not:** generic packing templates → Atlas (unless tied to a trip); budget buckets → Solace;
documents → Documents/Attachments; pet-care instructions → Pets (Travel can trigger them);
large non-travel projects → Projects.

## 3. Key features

**Trip** — title, destination, start/end date, status, description, visibility, participants
(people).
**Bookings** — type (flight, accommodation, transport, activity, restaurant, other), provider,
reference number, start/end time, location, notes, attachment, `calendar_event_id`.
**Packing** — list with `assigned_to_person` items, packed status, shared vs per-person items.
**Itinerary** — day-by-day, calendar-linked events, notes.
**Documents** — bookings, tickets, confirmations, passports (if permitted), insurance (via
shared attachments).

## 4. Permissions

Usually household-visible; sensitive details restricted: trip countdown visible to children;
booking references manager/admin only; passport documents sensitive; financial details
Solace-only.

## 5. Hub / Calendar / Notifications

Widgets: upcoming trip · trip countdown · packing progress · today's travel events · travel
tasks. Calendar (via helper): trip dates, flights, accommodation, bookings, activities,
preparation reminders. Notifications: trip approaching · packing incomplete · booking upcoming ·
document missing · passport/ID reminder (if enabled) · pet-care planning needed.

## 6. Events (signals)

Publishes: `trip_created`, `trip_upcoming`, `travel_booking_created`, `packing_item_created`,
`packing_complete`.
Consumes: `pet_care_required`, `solace_budget_updated`, `atlas_list_completed`.
Example: trip created → Pets prompts pet-care planning, Atlas creates a packing checklist,
Calendar receives trip events.

## 7. Search / Kiosk

FTS over trip titles, destinations, booking providers, itinerary items, packing items, notes,
attachment metadata. Kiosk: trip countdown, simple itinerary, packing checklist, upcoming
events — visual cards and countdowns for children.

## 8. Data model

`travel_trips`, `travel_bookings` (`calendar_event_id`), `travel_packing_items`
(`assigned_to_person_id`). Inherit `HouseholdBaseModel`.

## 9. Scope & completion

Initial: trips · bookings · packing lists · calendar integration · Hub countdown · attachments ·
basic permissions · kiosk countdown/packing view. Complete when users create trips, add
bookings, manage packing, attach documents, and see trip dates/countdowns on Calendar, Hub and
kiosk. Future: maps, weather, currency, travel journal, photo timeline, pet-care automation,
Solace budget integration, shared itinerary export.
