# Node Spec — Health

> Canonical. **Later node — built only after security maturation** (Roadmap M4). Sensitive
> throughout. Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Manages sensitive human health information for household members — reminders, appointments,
medications, allergies, immunisations, records and documents — in a secure, permission-
controlled area. Answers: *"What health information and reminders do authorised users need to
manage?"* **Security outranks convenience here.** All records are sensitive by default.

## 2. Belongs / does not belong

**Belongs:** doctor/dentist appointments, medication reminders, allergy information,
immunisation records, prescription renewals, test-result documents, provider details, medical
notes.
**Not:** pet health → Pets; general reminders → Atlas; school events → Education; (documents may
live in Documents/Attachments but link to Health); fitness goals → future, kept out of Health
V1.

## 3. Primary users

Admins/managers manage health records only if authorised. Users manage their own records.
Children have no Health access by default unless explicitly allowed.

## 4. Key features

**Health records** — person, record type, title, description, visibility, attachments.
**Medications** — name, dosage, frequency, start/end date, notes, reminder schedule.
**Appointments** — provider, date/time, location, notes, `calendar_event_id`.
**Allergies** — allergen, severity, notes, emergency guidance.
**Immunisations** — name, date, `next_due_at`, document attachment.
All subject fields reference a **person**; ownership/audit references a **user**.

## 5. Permissions (strong)

Visibility: private · user_restricted · manager/admin_restricted · sensitive. **Re-authentication
required** (password-based) via the central resolver. **All access audited.** Never appears in
unauthorised Hub, Calendar, Search or kiosk views.

## 6. Hub / Calendar / Notifications

Hub widgets restricted (upcoming appointment, medication reminder, prescription renewal) — never
on shared kiosk or child Hub by default. Calendar (via helper): appointments, medication
reminders, immunisation due dates, prescription renewals — **sensitive visibility by default**.
Notifications go only to authorised users; notification privacy carefully considered.

## 7. Events (signals)

Publishes: `health_appointment_created`, `medication_due`, `prescription_due`,
`immunisation_due`. Consumes very few events to reduce risk.

## 8. Search / Kiosk

Restricted FTS — results appear only after permission and sensitive-access checks; snippets must
not leak detail. No general kiosk interface in early versions (default hidden); emergency-safe
health cards only after careful design.

## 9. Data model

`health_records`, `health_medications`, `health_appointments` (`calendar_event_id`,
`recurrence_rule` where recurring). Inherit `HouseholdBaseModel`; `sensitivity = health`.

## 10. Scope & completion

Built only when sensitive-node security, audit logging, attachment permissions and re-auth are
fully working. Initial release: re-auth · appointments · medications · allergies · attachments ·
calendar integration · audit logs · restricted search. Complete only when health data can be
managed securely with all sensitive controls proven. Future: prescription tracking, health
graphs, provider directory, emergency health card, encrypted attachments, field-level
encryption, mobile biometric unlock.
