# Node Spec — Assets

> Canonical. **Later node** (post-V1). Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Manages household assets, valuables, vehicles, appliances, warranties, service records and
maintenance reminders — consolidating several would-be nodes into one domain. Answers: *"What
do we own, what needs maintaining, and what records do we need for it?"* Replaces separate
Vehicles, Warranties, Appliances, Tools and Home-Maintenance nodes.

## 2. Asset types

vehicle · appliance · electronics · tool · furniture · outdoor/garden · camping · home_system ·
other. Vehicle-specific fields appear only when `asset_type = vehicle`.

## 3. Belongs / does not belong

**Belongs:** car registration/service/insurance; appliance warranties; serial numbers; manuals;
receipts; service reminders; smoke-alarm replacement; camping gear details.
**Not:** consumable stock → Inventory; general notes → Atlas/Home Wiki; project work →
Projects; financial planning → Solace; sensitive human-health equipment → Health.

## 4. Key features

**Asset profile** — name, type, category, brand, model, serial number, purchase date, purchase
price (optional), warranty expiry, location, notes, photo, attachments; `visibility`.
**Maintenance** — type, `due_at`, `recurrence_rule`, `last_done_at`, provider, cost (optional),
notes, `calendar_event_id`.
**Documents** — receipt, manual, warranty, insurance, registration, service report (via shared
attachments).
**Vehicle details** (vehicles only) — registration number, registration/insurance due dates,
VIN, odometer, service interval, tyre details.

## 5. Permissions (sensitive)

Role-based visibility. General assets may be household-visible; vehicles and expensive/financial
assets manager/admin only; **children don't see Assets by default**. Registration, VIN,
insurance, serials and receipts are treated as sensitive (Security doc §11).

## 6. Hub / Calendar / Notifications

Widgets: maintenance due · warranty expiring · vehicle registration due · insurance renewal ·
recently added. Calendar (via helper): registration, insurance, warranty expiry, scheduled
service, maintenance, smoke-alarm checks, filter replacement; `recurrence_rule`.
Notifications: upcoming maintenance · warranty expiry · registration · insurance · service
overdue.

## 7. Events (signals)

Publishes: `asset_created`, `asset_warranty_expiring`, `asset_maintenance_due`,
`vehicle_registration_due`, `asset_document_added`.
Consumes: `attachment_uploaded`, `project_completed`, `inventory_item_used`.
Example: receipt uploaded → Assets links it to an asset → warranty reminder created. Also:
`asset_manual_added` lets Home Wiki link the manual to a reference page.

## 8. Search / Kiosk

FTS over asset names, serials, models, warranty info, service notes, document metadata —
permission-enforced. Not a primary kiosk node; kiosk may show safe maintenance reminders only;
children never see vehicles/warranties/purchase details by default.

## 9. Data model

`assets`, `asset_maintenance_records` (`recurrence_rule`, `calendar_event_id`),
`asset_documents`, `vehicle_details` (vehicles only). Inherit `HouseholdBaseModel`.

## 10. Scope & completion

Initial: asset profiles · types · attachments · warranty expiry · maintenance reminders ·
vehicle registration/service reminders · calendar integration · Hub widget · basic permissions.
Complete when users create assets, attach documents, track warranty/maintenance dates, and see
reminders on Hub and Calendar. Future: cost tracking, provider list, odometer-based reminders,
QR labels, depreciation, maintenance templates, warranty-claim/insurance trackers.
