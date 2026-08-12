# Capability Spec — Assets & Vehicles (former Assets plan)

> **Status:** future proposal, not implemented as a current top-level node. Home appliances,
> warranties, rooms and home maintenance already belong to Homestead (D21). The preferred future
> direction is an optional **Homestead → Assets & vehicles** capability for remaining non-home
> asset/vehicle scope, if real household use justifies it.

## 1. Purpose

Assets & vehicles would answer:

- What significant non-home items/vehicles do we own?
- What identifying/warranty/service records matter?
- What maintenance/registration/insurance action is due?

It should not duplicate Homestead's existing home appliance/property records simply to create a
more generic asset catalogue.

## 2. Ownership boundaries

### Already owned by Homestead

Do not recreate these in Assets:

- home appliances;
- home-system equipment;
- appliance warranty/manual/serial context;
- room/property association;
- ordinary home maintenance;
- home service providers;
- household cover/cost context already modelled by Homestead/Solace.

### Potential Assets & vehicles ownership

- vehicles;
- tools;
- electronics/valuable equipment not naturally Homestead room/appliance records;
- camping/outdoor equipment where structured ownership/service detail is useful;
- registration/service/insurance context for vehicles;
- serial/VIN/identifying information;
- non-home warranty/service history;
- protected related documents.

### Belongs elsewhere

- consumables/stock → future Stock & storage capability;
- ordinary shopping wish → Atlas Shopping/Corner;
- finance/payment schedule → Solace;
- project work → existing owning domain, with Projects still evidence-gated;
- medical equipment/records needing medical privacy → Health;
- binary files → shared Attachments.

## 3. Capability position

If implemented, Assets & vehicles should normally appear inside Homestead/Manage HomeStack as an
optional protected capability rather than another top-level navigation item.

This is a presentation/product direction, not permission to reuse Homestead appliance rows for
vehicles indiscriminately. The data model should preserve clear type-specific fields and security.

Do not build a separate Assets node now and assume later consolidation will be free; the preferred
direction should be respected from the first implementation.

## 4. Candidate records

Only add models when the capability is approved.

### Asset / Vehicle

Potential common fields:

- name/type/category;
- brand/model;
- serial/identifier;
- purchase date/value context where useful;
- location;
- notes;
- image/attachments;
- visibility/sensitivity.

Vehicle-specific fields can include:

- registration;
- VIN;
- registration/insurance due dates;
- odometer/service interval;
- tyre/service notes.

Avoid a sparse universal table full of irrelevant nullable fields if actual vehicle/tool workflows
need cleaner subtype models.

### Maintenance / service history

Potential fields:

- owning asset/vehicle;
- service/maintenance type;
- due date/recurrence;
- last-completed/service date;
- provider;
- notes;
- optional cost context;
- Calendar projection where meaningful.

## 5. Permissions and sensitivity

This capability is more sensitive than ordinary household lists.

Examples requiring stronger access consideration:

- VIN/registration identifiers;
- insurance/policy information;
- expensive asset serials/receipts;
- purchase-value/history;
- protected documents.

Children should not see this capability by default. General household members may receive only the
safe maintenance reminder/detail their permission allows.

Do not assume that placing it visually under Homestead makes every field household-visible.

## 6. Calendar / notifications

Meaningful owner dates can project through the shared scheduling helper:

- registration renewal;
- insurance renewal;
- scheduled service;
- warranty expiry;
- recurring maintenance.

Notifications use the shared Notifications/Web Push system and must avoid exposing protected
identifiers/financial detail on lock screens.

## 7. Hub and Search

Potential Hub summaries:

- maintenance due;
- warranty/registration/insurance expiry;
- vehicle service overdue.

Search should be permission-aware, particularly for serial/VIN/registration/document metadata.

Neither Hub nor Search becomes an easier route to protected asset information.

## 8. Attachments

Receipts, manuals, warranties, insurance/registration documents and service reports use the shared
protected attachment service.

A file's raw storage path is never authorization.

Home Wiki may link to a safe manual/reference page, but the structured asset record remains owned by
this capability/Homestead boundary.

## 9. Events and cross-domain relationships

Use D4/shared services rather than model imports.

Possible future interactions:

- maintenance completed → publish an asset/vehicle event;
- Solace → link financial budget/bill context without Assets owning payment history;
- future Projects → reference a vehicle/asset if a real project workflow later exists;
- Home Assistant → selected status only where the dedicated HA bridge owns that integration.

## 10. Mobile / kiosk

Responsive web/mobile should prioritize quick access to service/registration/warranty information
and history.

This is not a primary kiosk/child domain. A safe maintenance reminder may surface through Hub/
Calendar, but detailed vehicle/value/identifier screens remain restricted.

## 11. Future enhancements

Only after a useful basic capability exists:

- odometer-driven maintenance;
- QR labels;
- warranty claims;
- depreciation/reporting;
- richer insurance tracking;
- maintenance templates;
- cost-of-ownership analysis.

Finance analysis should still use/coordinate with Solace rather than silently create a second
budget ledger.

## 12. Implementation gate

Do not implement because an early HomeStack plan contained an Assets node. Implement only when the
household has enough non-home vehicle/tool/valuable-item workflows that Homestead's existing home
records and Atlas notes are insufficient.

If approved, completion means the household can manage the selected non-home assets/vehicles,
protect identifiers/documents, track meaningful due dates and surface safe reminders—without
recreating Homestead's already-owned home-appliance/warranty data.