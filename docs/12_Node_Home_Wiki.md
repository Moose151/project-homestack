# Node Spec — Home Wiki

> **Status:** shipped and in household use. Home Wiki is the persistent household knowledge base.
> A future proposal may present this content as a Homestead **Household guide** capability, but
> that consolidation has not been implemented and does not change current data ownership.

## 1. Purpose

Home Wiki stores information the household expects to look up repeatedly: procedures, emergency
reference, technology/Wi-Fi instructions, house-running knowledge, contacts and other durable
reference material.

It answers: **Where do we keep household information that should still be useful months from now?**

## 2. Ownership boundaries

**Home Wiki owns:**

- durable household reference pages;
- categories/tags/favourites;
- emergency/reference page presentation flags;
- kiosk-safe reference content;
- review/reminder metadata where implemented.

**Belongs elsewhere:**

- temporary notes/lists → Atlas;
- protected raw files → shared Attachments linked to the appropriate owner;
- property/room/appliance structured records → Homestead;
- finance → Solace;
- pet structured care/history → Pets;
- medical information → Health;
- large home improvements → Homestead;
- future non-home project boards → only a Projects domain if real use later justifies one.

Home Wiki may link to another domain's structured record/file without copying ownership.

## 3. Pages and categories

Wiki pages support the implemented useful combination of:

- title/body;
- category/tags;
- favourite state;
- emergency/kiosk-safe presentation flags;
- visibility/sensitivity;
- attachments/links where appropriate.

Categories keep browsing understandable but should not become a deep taxonomy. The household can
add/hide/manage categories according to current UI permissions.

## 4. Favourites and emergency information

Favourite pages provide quick access to commonly referenced household knowledge.

Emergency pages may deliberately be more discoverable, but **emergency visibility is not a bypass
of sensitive data rules**. A page can expose safe instructions while protected personal/account/
medical information remains in its owning protected domain.

Examples of useful Wiki content include:

- Wi-Fi/router procedures;
- power/water outage procedures;
- bin/house routines;
- safe emergency contacts/instructions;
- pet/house-sitter instructions;
- appliance usage guidance;
- kiosk/how-to guidance.

Where Homestead already owns structured emergency/property locations, the Wiki should link or
explain rather than maintain a second conflicting structured value.

## 5. Permissions and kiosk

Pages follow central visibility/permission filtering.

- children/kiosk see only explicitly safe permitted content;
- sensitive/private/adult pages remain hidden even if the category itself is visible;
- kiosk is primarily read-focused and easy to return from;
- attachment access is independently permission checked through the shared service.

UI flags such as `is_kiosk_safe` help presentation but backend permissions remain authoritative.

## 6. Hub / Search / Notifications

Home Wiki can contribute permission-aware favourites/emergency/recent-reference shortcuts to Hub.

Search is especially important for this domain and must filter source pages before snippets are
created.

Notifications should remain sparse and useful (for example a review reminder) rather than turning a
reference wiki into a noisy task system.

## 7. Calendar

Most Wiki content is timeless reference. Date-based review/reminder records, where used, follow the
shared Calendar ownership/scheduling helper rather than maintaining an independent reminder engine.

Do not add Calendar events simply because a page exists.

## 8. Events and cross-domain relationships

Home Wiki can publish meaningful page lifecycle/reference events through D4. Other domains can link
to Wiki pages without importing Wiki models.

Old examples that assumed a future top-level Assets node are not architectural requirements. Home
appliance/serial/warranty structure already belongs to Homestead; the Wiki may hold human-readable
instructions or link to the structured record/manual.

## 9. Attachments

Files use shared Attachments. Home Wiki does not implement its own file storage/security.

Sensitive attachments never become kiosk/public simply because they are linked from a kiosk-safe
page.

## 10. Mobile experience

Prioritize quick search, favourites, readable long-form reference and simple editing. A household
member should be able to find an instruction on a phone without navigating a deep category tree.

## 11. Data ownership

Exact schema is defined by current Django models/migrations. Home Wiki owns its page/category data;
shared Attachments, Search, Hub and Calendar remain projections/services around that source.

Page version history, richer templates/linked-page graph, OCR/AI and house-sitter modes remain
optional future enhancements.

## 12. Capability-consolidation proposal

`31_Core_Manage_HomeStack.md` proposes a future **Homestead → Household guide** capability to reduce
top-level navigation if that proves desirable.

Until explicitly implemented:

- Home Wiki remains its own current node/domain;
- do not migrate/delete its records;
- do not claim the Homestead capability exists;
- any future presentation consolidation must preserve existing data, permissions, Search/Hub
  behavior and stable links.

## 13. Completion state

The current baseline is complete: pages/categories, favourites/emergency/reference behavior,
permission-aware search, attachments, Hub contributions and kiosk-safe reading are available.

Future work should improve reference usefulness (revision history/templates/linking) only when real
household use demonstrates the need.