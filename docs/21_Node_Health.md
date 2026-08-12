# Node Spec — Health

> **Status:** future sensitive domain. The generic sensitive-node machinery (M4) is already
> functionally complete, but Health remains deliberately deferred until HomeStack's production
> serving, recovery/backups and stronger adult remote-auth posture are mature enough for medical
> information. Fitness & Training is already shipped separately and must remain outside this
> medical privacy boundary (D24).

## 1. Purpose

Health manages sensitive human medical information for household members: appointments,
medications, allergies, immunisations, records and protected documents.

It answers: **What health information and reminders do authorised household members need to manage
safely?**

Security/privacy outrank convenience. Health should not be enabled merely because HomeStack already
has a generic sensitive-node lock.

## 2. Ownership boundary

**Health owns:**

- medical appointments/providers;
- medications/prescriptions;
- allergies/intolerances where treated as medical records;
- immunisations;
- test/result/medical notes;
- medical documents;
- future health measurements/trends where deliberately approved.

**Health does not own:**

- workouts/training programs/performance records → Fitness & Training;
- pet health → Pets;
- ordinary reminders → Atlas;
- school information → Education;
- general protected file plumbing → shared Attachments;
- household finance → Solace.

Diagnoses, medications, injuries, body measurements and medical notes must never drift into Fitness
for convenience (D24).

## 3. Privacy posture

Health records are sensitive by default.

Required principles:

- backend permission enforcement;
- explicit Person subject and User actor distinction (D12);
- password re-authentication for protected access;
- audit of meaningful sensitive access/actions;
- no ordinary child/kiosk exposure;
- private/sensitive Calendar projections;
- Search filtering before snippets;
- sparse notification/push payloads;
- protected attachment download path;
- no accidental disclosure through Hub/Corners/Agenda.

Standard Users may eventually manage their own Health records where the permission model explicitly
allows it. Adult/admin role alone should not be assumed to authorize every person's medical data.

## 4. Prerequisites before implementation

Do not begin the Health domain until these are reviewed as sufficiently mature for medical data:

- generic sensitive-node re-authentication/locking — already implemented;
- permission/visibility/audit/attachment spine — already implemented;
- trusted HTTPS — already implemented on LAN;
- **production application serving**, replacing development servers in the live path;
- **encrypted off-server backup/recovery** and tested restore routine;
- stronger adult/admin remote authentication (2FA/passkeys) before any remote/public medical
  access;
- notification privacy behavior proven by the Web Push work;
- explicit Health threat-model/privacy review.

If HomeStack remains LAN/VPN-only, that can reduce exposure, but it does not remove the backup,
shared-device or intra-household privacy requirements.

## 5. Initial record types

A first useful slice can include:

### Appointments

- Person;
- provider/service;
- date/time/location;
- notes;
- visibility/sensitivity;
- optional attachments;
- source-linked sensitive Calendar projection.

### Medications / prescriptions

- Person;
- medication name;
- dosage/instructions;
- start/end/current state;
- reminder/renewal schedule where required;
- notes/document linkage.

### Allergies

- Person;
- allergen;
- severity/notes;
- emergency guidance where appropriate.

### Immunisations

- Person;
- vaccination/immunisation;
- administered date;
- next due date where known;
- protected document linkage.

### General medical records

A deliberately simple protected record/attachment container for results, provider letters and
other health notes that do not fit a more specific structured type.

Avoid creating dozens of medical subdomains in the first release.

## 6. Calendar

Health owns the medical source record. Calendar receives only the necessary source-linked
projection through the scheduling helper (D7).

A Calendar row visible to an authorised User can be deliberately generic if exposing a provider,
condition or medication name is unnecessary. Calendar must not become a less protected copy of the
Health record.

## 7. Notifications / Web Push

Health notifications require the strictest payload treatment.

A lock-screen push should normally say something generic such as "You have an upcoming health
reminder" rather than reveal medication, diagnosis, provider or appointment detail.

Opening the notification must re-establish session/permission/re-auth as required before fetching
the source detail.

Health uses the shared notification preference/device infrastructure, not a separate notification
channel.

## 8. Search / Hub / Corners / kiosk

- Search includes Health only after sensitive permission/elevation checks and builds snippets only
  from authorised records.
- Hub may show generic authorised reminders; no shared/child kiosk Health widgets by default.
- Corners should not casually aggregate medical history/activity. Any future Health contribution
  requires an explicit privacy decision rather than normal Corner auto-discovery.
- Kiosk has no ordinary Health browsing surface. Emergency-safe presentation, if ever added, is a
  separate carefully scoped feature.

## 9. Attachments

Health documents use the shared attachment service with medical sensitivity/visibility and audited
protected downloads.

Raw file URLs/storage paths must never bypass the application permission boundary.

Possible future stronger encryption for medical attachments/fields is evidence/threat-model driven;
it should not be implemented as an unreviewed one-off crypto layer.

## 10. Events and integrations

Health should consume/publish as little cross-domain content as practical.

Any approved event payload contains the minimum non-sensitive information necessary. Financial,
Fitness or Home Assistant integrations must not receive medical detail simply because they consume
generic HomeStack events.

Home Assistant should not become a medical sensor/history database for HomeStack unless a future
separate health/device decision explicitly defines that boundary.

## 11. Data ownership

Exact schema will be defined by models/migrations when implementation begins. Candidate data
families are Health records, medications, appointments, allergies and immunisations, all
household-scoped with Person subjects and sensitive defaults.

Do not pre-create a large speculative medical schema before the first real household workflows are
agreed.

## 12. Initial completion criteria

Health is ready for household use only when:

- an authorised User can manage their permitted medical appointments/medications/allergies/
  immunisations and documents;
- password re-auth/security behavior works consistently;
- a second household User without permission cannot discover the data through direct API IDs,
  Calendar, Hub, Search, Corners, notifications or attachments;
- shared/kiosk devices do not retain exposed sensitive state;
- backups containing Health data have the stronger protected recovery path;
- Web Push tests prove medical detail does not appear on an unauthenticated lock screen;
- audit entries are useful without copying sensitive medical content into audit metadata.

## 13. Later possibilities

Only after the baseline proves useful:

- prescription renewal tracking;
- health measurements/trend graphs;
- provider directory;
- emergency health card;
- more granular encrypted health fields;
- mobile biometric/passkey-assisted unlock;
- health-device integrations with separately reviewed privacy boundaries.

Health should remain intentionally narrower and more conservative than Fitness or ordinary
household domains.