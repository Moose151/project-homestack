# Node Spec — Pets

> **Status:** shipped and in household use. Pets owns household pet profiles, treatment/care
> reminders and appointments. The node is household-generic (D15): no fixed pet count, species or
> household-specific names are encoded in schema/business rules.

## 1. Purpose

Pets answers: **What do we need to know or do for the household's pets?**

It supports a light setup (one pet + one reminder) and can hold more detailed care history without
forcing every household to track everything.

## 2. Ownership boundaries

**Pets owns:**

- pet profiles;
- flea/worming/vaccination/medication/grooming treatment schedules;
- vet appointments;
- pet-specific care notes/instructions;
- pet-specific identifiers/insurance context where implemented;
- pet-related attachments/history.

**Belongs elsewhere:**

- pet-food stock-on-hand → future Stock & storage/Inventory capability if implemented;
- ordinary pet-food Grocery purchase → Atlas Grocery;
- rewarded "feed/walk pet" household chore → Meridian;
- trip itinerary → Travel (which may later trigger a pet-care handoff);
- human medical information → Health;
- raw file storage/security → shared Attachments.

Pets should remain fully useful without future Inventory/Stock being enabled.

## 3. Pet profiles

A Pet profile includes the implemented useful combination of name, species/breed, avatar/photo,
date/context, colour, notes, vet details, microchip/insurance/food-care information and relevant
visibility.

Sensitive identifiers/documents follow the normal permission/attachment boundary rather than being
assumed safe merely because ordinary pet information is household-visible.

## 4. Treatments

A treatment owns its `next_due_at`/recurrence and related care details.

Typical treatment types include flea, worming, vaccination, medication, grooming and other
recurring pet care.

Completion records `last_done_at` and advances the next due date according to the RRULE/current
service behavior. Non-recurring treatments clear future reminder state rather than recreating
another occurrence.

The owning treatment remains the source of truth; Calendar projection is maintained through D7.

## 5. Appointments

Vet/other pet appointments own their provider/date/time/location/notes and project into Calendar
through the shared scheduling helper.

Attachments such as vaccination certificates or vet paperwork use the shared protected file
service.

## 6. Permissions

Most ordinary pet-care data may be household-visible, while individual records/identifiers/
documents can use the shared restricted/sensitive visibility rules.

Children/kiosk see only safe permitted care information/actions. Adult visibility of one pet record
does not imply unrestricted access to every linked attachment/insurance identifier.

## 7. Hub / Calendar / Notifications

Useful Pets projections include:

- treatments/reminders due or overdue;
- upcoming appointments;
- relevant medication/care tasks;
- simple pet profile/care summaries.

Calendar mirrors owning record dates through D7.

Notifications use the shared Notifications/Web Push infrastructure rather than a Pets-specific
channel. A future low-pet-food signal can originate from Stock & storage if that capability is ever
implemented; Pets must not depend on it for ordinary operation.

## 8. Events and cross-domain relationships

Pets publishes meaningful lifecycle/care events through D4. Future relationships can include:

- Travel trip created/approaching → prompt safe pet-care/house-sitter planning;
- Meridian → rewarded pet-care task relationship;
- future Stock & storage → pet-food low suggestion.

Those interactions must not be implemented by importing another domain's models into Pets.

## 9. Search / attachments

Search covers permitted pet/profile/treatment/appointment content according to current selectors.
Sensitive details are filtered before snippets.

Photos/vet records/vaccination certificates/insurance documents use shared Attachments.

## 10. Mobile and kiosk

Pets is a visual household domain:

- pet cards/photos;
- today's care/reminders;
- large completion actions;
- upcoming appointments;
- simple instructions.

Kiosk/child surfaces minimize typing and omit adult/private data.

## 11. Data ownership

Exact schema is defined by current Django models/migrations. Main Pets families are profiles,
treatments and appointments plus any current pet-specific detail/history models. Calendar,
notifications, Hub, Search and Attachments are shared projections/services around them.

## 12. Completion state

The useful Pets baseline is complete: profiles, recurring treatment/reminder behavior, treatment
completion/advancement, appointments, Calendar/Hub/search/attachments and responsive household
presentation are available.

Future work should be evidence-driven: richer feeding schedules, weight trends, sitter mode,
insurance workflow, Meridian pet chores or Travel handoff—not required dependencies on future
Inventory/Stock.