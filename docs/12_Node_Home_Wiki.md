# Node Spec — Home Wiki

> Canonical. **V1 node.** Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose

Home Wiki is the household knowledge base: persistent information the household references
repeatedly, that doesn't belong in a temporary note, checklist, project, document vault or
calendar entry. It answers: *"Where do we keep the information we may need to look up later?"*
— WiFi, emergency info, appliance instructions, bin schedules, procedures, contacts, utility
details.

## 2. Philosophy

For information that stays useful over time. Short-term notes/lists → Atlas. Secure files →
Documents/Attachments. Large initiatives → Projects. Home Wiki is clear, searchable,
organised, easy to update, kiosk-safe where appropriate, and useful in emergencies. It should
end repeated questions like "what's the WiFi password?", "when is bin night?", "how do I reset
the router?", "who do we call in an emergency?"

## 3. What belongs

WiFi details; router reset; bin schedule; emergency contacts; water shutoff/switchboard
location; appliance instructions; utility/internet provider details; vet/school contacts;
house rules; routines; "how to use the kiosk"; cleaning notes; where things are stored;
house-sitter and pet-sitter instructions; evacuation notes.

## 4. What does NOT belong

Temporary notes/lists → Atlas. Large initiatives → Projects. Sensitive scanned files (e.g.
passport scan) → Documents/Attachments. Medical records → Health. Bills/budgets → Solace.
Warranties/serials/service history → Assets. Home Wiki may *link* to these but never owns them.

## 5. Primary users

Admins, managers, users, permitted children, kiosk users, future guest/house-sitter accounts.
Children may see safe pages (morning routine, emergency contacts, pet feeding, kiosk help) but
never private/sensitive/adult-only pages.

## 6. Key features

**Wiki pages** — title, body, category, tags, visibility, attachments; `created_by/updated_by`
= user. V1 plain/basic rich text; Markdown/templates/linked pages parked. `is_kiosk_safe`
flag.

**Categories** — suggested defaults: Emergency, Internet & Technology, Utilities, Appliances,
Household Procedures, Cleaning, Pets, School, Contacts, House Sitting, Manuals, Miscellaneous.
Admins can add/edit/hide/reorder.

**Favourite pages** — pinned to the top of Home Wiki, Hub, kiosk and emergency mode (e.g.
emergency contacts, WiFi, bin night, pet feeding, router reset).

**Emergency information** — a dedicated area (address, emergency/doctor/dentist/vet contacts,
poison hotline, water shutoff, switchboard, procedures, evacuation notes). Carefully
permissioned: some kiosk-safe, sensitive personal detail protected.

**Procedures** — step-style pages (router reset, washing machine, school lunches, feeding
pets, bin night, power outage). Procedure checklist blocks parked.

**Attachments & manuals** — link PDFs/photos/manuals via the shared service. No own storage.

**Templates** — parked (appliance, emergency contact, utility, procedure, pet-care,
technology, house-sitter pages).

## 7. Permissions

Visibility: private · household · role_restricted · user_restricted · kiosk_safe · sensitive.
Default household. Emergency pages may be broadly visible but sensitive detail restricted.
Children see only safe pages; future guests see only specifically shared pages.

## 8. Hub integration

Widgets: favourite pages · emergency-info shortcut · recently updated · bin-night reminder ·
household notice · quick links · kiosk help. Permission-aware (a child sees only safe items).

Completion rule: this node is not "done" until its Hub widget rows are seeded with
`source_node` set, kiosk support declared per widget, and content is supplied through
permission-filtered selectors that the Hub service calls without cross-node model imports.

## 9. Calendar integration

Mostly reference, so few events. Some pages carry date-based reminders (bin night, filter
replacement, review reminders) — created via the scheduling helper with `calendar_event_id`,
recurrence as `recurrence_rule`.

## 10. Notifications

Optional and sparing: review this page · procedure outdated · emergency contacts need review ·
manual added · page assigned for reading.

## 11. Events (signals)

Publishes: `wiki_page_created/updated/deleted`, `wiki_page_marked_favourite`,
`wiki_emergency_page_updated`. Consumes: `asset_manual_added`,
`pet_care_instruction_updated`, `household_setting_changed`. Example: Assets uploads a manual →
`asset_manual_added` → Home Wiki links it to the appliance reference page.

## 12. Search

Highly searchable: page title/body, category, tags, attachment metadata, linked records — via
FTS, permission-filtered. Home Wiki is effectively the household memory system; search is its
most important feature.

## 13. Attachments

PDFs, photos, screenshots, reference docs, procedure images — via the shared service.
Sensitive attachments never exposed on kiosk/child accounts unless explicitly permitted.

## 14. Kiosk

Favourite pages, emergency info, simple browsing, large category cards, search, read-only for
children, easy return to Hub. Kiosk-safe pages clearly marked; sensitive pages never exposed.

## 15. Mobile

Quick search, favourites, easy reading, simple editing, attachment viewing, category browsing
— useful for checking household instructions while away from the kiosk.

## 16. Progressive detail

Basic: create page, add text. Standard: categories, tags, attachments, favourites, visibility.
Detailed: templates, linked pages, page history, review reminders, emergency/house-sitter mode.

## 17. Data model

`wiki_pages` (`is_kiosk_safe`, `visibility`, `calendar_event_id` where dated). `wiki_page_versions`
deferred but schema-anticipated. All inherit `HouseholdBaseModel`. Shared: attachments, tags,
categories, calendar_events, notifications, audit_logs.

## 18. V1 scope

Create/edit/delete pages · categories · basic formatting · tags · favourites · attachments ·
FTS · permission-aware visibility · kiosk-safe read view · emergency-info section · Hub
favourite-pages widget. Not in V1: full page history, rich templates, linked-page graph, OCR,
AI summarisation, public sharing.

## 19. Risks & mitigation

Risk: overlap with Atlas/Documents, sensitive info leaking to kiosk, clutter, stale pages, too
many categories. Mitigation: Atlas for temporary, Home Wiki for long-term; clear visibility
labels; favourites; review reminders later; few categories; strong search.

## 20. Completion criteria

Create/edit/delete pages; categorise, tag, attach, favourite; search; permissions enforced;
kiosk-safe pages viewable from kiosk; emergency info configurable; Hub shows favourites;
Hub widget rows/selectors are shipped; follows the shared design system.
