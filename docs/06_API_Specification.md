# Document 6 — API Specification

> **Canonical API contract.** Exact currently registered routes are defined by Django URLconfs and
> tested API behaviour. This document defines stable conventions, security requirements and route
> ownership. Avoid maintaining a second brittle copy of every endpoint as the application evolves.

## 1. Base contract

Base path:

```text
/api/v1/
```

Current web/kiosk/PWA clients use Django session authentication. Native token authentication is
future work (D6).

The API is the business/security boundary. React components, deep links, notification payloads and
kiosk state never grant authority by themselves.

## 2. Route ownership

Top-level route groups map to the owning core service or domain, for example:

```text
/api/v1/auth/
/api/v1/users/
/api/v1/people/
/api/v1/household/
/api/v1/nodes/
/api/v1/hub/
/api/v1/calendar/
/api/v1/notifications/
/api/v1/attachments/
/api/v1/search/
/api/v1/backups/
/api/v1/audit-logs/

/api/v1/atlas/
/api/v1/meridian/
/api/v1/education/
/api/v1/wiki/
/api/v1/pets/
/api/v1/books/
/api/v1/homestead/
/api/v1/solace/
/api/v1/fitness/
/api/v1/travel/
```

Future Home Assistant routes live under a dedicated Home Assistant namespace. Do not create a
generic `/integrations/` API merely to host it (D22).

There is no public/internal HTTP `/events/` bus API; D4 events are an application-internal boundary.

## 3. Exact route source of truth

For exact current method/path names, use:

1. `backend/config/urls.py`;
2. each registered `backend/apps/*/urls.py`;
3. view/API tests;
4. this document for cross-cutting contract.

When a route ships or is removed, update the owning node/core spec and tests. Do not leave obsolete
endpoint lists here (for example a removed native-Solace concept) merely because it appeared in an
earlier design.

## 4. Authentication endpoints

The authentication API includes the current session/PIN/password flows, conceptually:

```text
PIN login
password login
logout
current user/session (`me`)
password re-authentication / sensitive elevation
kiosk-safe login-user discovery where deliberately unauthenticated
```

Important rules:

- login endpoints are the only places that accept credentials for establishing/elevating a
  session;
- re-auth uses adult password rather than PIN;
- failed login/reauth must not disclose unnecessary account/security detail;
- brute-force/rate-limit hardening is required before public remote exposure;
- CSRF/session cookie behaviour must match the deployed HTTPS/proxy settings.

## 5. Authorization and visibility (D10)

Every protected request is subject to the applicable combination of:

- authentication;
- active User status;
- household scope;
- role/per-user permission;
- node/capability enablement;
- record visibility/sensitivity;
- child/kiosk restrictions;
- current sensitive re-authentication state.

List endpoints must filter inaccessible records in selectors/querysets rather than serialize them
and remove them later.

Domain membership/ownership can add an extra constraint. For example, Books personal shelf entries
are scoped to the authenticated User and Book Club data is filtered to clubs the User belongs to.

For sensitive resources, returning 404 instead of confirming an inaccessible record's existence may
be appropriate where the existing contract uses that behaviour.

## 6. Users and People

User/account routes own login-capable accounts, roles, PIN/password resets, activation state and
Person linkage.

People routes own household profiles used as record subjects/assignees.

Do not use User IDs as a substitute for Person IDs in domain APIs simply because most current
household members have both (D12). Conversely, genuinely login-personal state such as one User's
Books shelf/rating may correctly be User-scoped.

## 7. Nodes / Manage HomeStack

Node/settings APIs expose the household's enabled/hidden/locked/configured domain state subject to
administrative permission.

Rules:

- disabling/hiding a node does not delete its data;
- node configuration does not bypass per-record permissions;
- proposed future capability consolidation must preserve data and security when a capability is
  hidden/restored.

## 8. Hub

Hub endpoints return permission-aware widget content and widget configuration. Each widget's data is
computed from source selectors rather than copied into an independent Hub data store.

Kiosk Hub requests receive only kiosk-safe permitted widget content.

## 9. Calendar / scheduling (D7/D8/D23)

Calendar APIs cover:

- standalone Calendar-owned event/appointment CRUD;
- permission-filtered time-window queries/views;
- generic rotating-schedule configuration/occurrence calculation/exceptions;
- source/deep-link information for node-owned projected events.

Node-derived event CRUD is not performed by clients against Calendar as though the projection were
the owner. Changes go to the source domain; the scheduling helper maintains the mirror.

Rotating schedule occurrence queries calculate bounded requested ranges rather than return stored
daily event rows.

## 10. Notifications and Web Push

The current in-app notification API supports listing and user actions such as read/dismiss state.

The active Web Push work extends this domain with the device/subscription/preference contract in
`32_Core_Notifications_and_Push.md`. When it lands, that spec plus registered URLconfs are the
source of truth for exact push endpoint names.

Security requirements:

- device subscriptions belong to the authenticated User/household;
- one User cannot manage another User's subscriptions/preferences without explicit admin contract;
- push payloads are sparse and sensitive-safe;
- opening/deep-linking from push re-checks current permissions/re-auth;
- expired/invalid subscriptions can be deactivated safely without deleting unrelated notification
  history.

## 11. Attachments

Attachment APIs provide upload/list/download/delete/link behaviour as implemented by the shared
service.

Every download is permission checked. Sensitive downloads are audited. An attachment path/storage
URL is never treated as authorization.

## 12. Search and shared link import

Global search is permission-aware and aggregates results from owning domain selectors/querysets.

Query strings do not bypass source permissions and snippets must not be built from inaccessible
records.

Safe URL/ISBN/product preview/enrichment uses the bounded shared Link Import API/service rather than
arbitrary node-specific fetch proxies. After review/save, the owning domain record is authoritative.

## 13. Audit and backups

Audit APIs are administrative/read-only except for internal logging helpers.

Backup APIs are administrative and include creation/listing/download/restore behaviour implemented
by the backup service. Restore is a sensitive re-authenticated operation.

## 14. Atlas

Atlas APIs own:

- notes;
- lists/items;
- reminders;
- Grocery;
- Shopping;
- item completion/edit/assignment/due-date behaviour;
- Agenda/appointments/events projection helpers where exposed by Atlas UI.

Product/link enrichment uses the bounded shared link-import capability rather than arbitrary server
fetch endpoints.

## 15. Meridian

Meridian APIs own the household task/reward/economy domain, including the implemented combination
of:

- tasks and task completions/review;
- routines;
- points/ledger/balances;
- rewards/shop/purchase approvals;
- categories/settings;
- goals/wishes/related contribution workflows;
- reports/leaderboard/achievement-related views where applicable.

The exact endpoint catalogue is defined by Meridian URLconfs/tests. Do not regress to the earlier
reduced endpoint list from the first port.

## 16. Education

Education APIs own institutions, profiles/courses, assessments, notes/files, timetable/class
records and Education events/search as implemented.

Dated assessments/events use the Calendar integration contract rather than a second independent
schedule API.

## 17. Home Wiki

Wiki APIs own pages/categories/favourite/emergency/presentation behaviour. Kiosk-safe read surfaces
must remain explicitly permission/presentation constrained.

## 18. Pets

Pets APIs own pet profiles, treatment/care schedules and appointments. Treatment completion advances
or clears future due state according to the owning recurrence rules and keeps Calendar projection in
sync.

## 19. Books

Books is a shipped opt-in domain with its own API namespace. Current route families cover:

- available active HomeStack Users used by Book Club membership UI;
- Book catalogue list/create/detail/update/delete;
- rating/notes upsert;
- personal shelf list/create/update/delete;
- Book Club list/create/detail/update/delete;
- club membership add/remove;
- club-book list/add/update/remove;
- ordered club queue list/add/reorder/remove.

Important security/ownership rules:

- `PersonalBookEntry` reads/writes are scoped to the authenticated User;
- each User has one `BookRating` per Book, shared across personal and club presentation;
- club list/detail/book/queue selectors return clubs the authenticated User belongs to;
- knowing a Book Club/member/queue ID does not bypass membership plus central Books permission;
- exact current paths are defined by `backend/apps/books/urls.py` and tests.

Book metadata enrichment from a URL or ISBN uses the shared safe Link Import boundary; Books does
not expose a generic scraper/fetch endpoint.

## 20. Homestead

Homestead APIs own property/room/area planning, maintenance, appliances, providers, cover/context,
pools/spas, utilities and floor-plan associations as implemented.

Protected finance-related Homestead actions must preserve the Solace permission/re-auth boundary
when they read or create Solace-owned financial records.

## 21. Solace / Money

Solace APIs own the current native finance model: bills/occurrences, pay-cycle/Now/forecast/bucket
and other implemented Money workflows.

Treat current Solace URLconfs/tests as authoritative. Do not re-add obsolete route groups (for
example a separate subscriptions surface after subscriptions were consolidated into Bills) just
because an older API document listed them.

All sensitive finance endpoints are permission/re-auth protected and must not leak content through
error messages, Hub, Calendar, Search or notifications.

## 22. Fitness & Training (D24)

Fitness APIs own:

- exercise catalogue/custom exercises;
- programs/program days;
- workout/session lifecycle;
- session exercises/sets and live editing;
- history/personal records/last-performance data.

Private/visible session rules are enforced on the backend. Fitness APIs must not become a medical
Health API.

## 23. Travel

Travel APIs own:

- trips and To-go/idea records;
- participant and surprise/hidden-user behaviour;
- booking/cost planning;
- idea-to-trip conversion where implemented;
- itinerary/Things-to-do records including dated/undated options;
- day-trip vs multi-day trip rules.

Dated/book-by itinerary/booking/trip elements follow the shared Calendar ownership rules. Hidden
Users must not recover surprise trip details by guessing IDs or using Calendar/search projections.

## 24. Home Assistant (planned, D22)

When implemented, Home Assistant APIs are backend-mediated and bounded. Candidate route families
include:

- connection health/test;
- entity discovery for admins;
- entity mappings;
- selected current state;
- action mappings and execution;
- event mappings/test.

The browser never receives the HA long-lived token and never submits arbitrary domain/service/entity
calls as a generic proxy.

## 25. Standard request/response behaviour

Use consistent status/error behaviour across domains.

Expected broad semantics:

- `200/201/204` for successful read/create/no-content operations as appropriate;
- `400` for validation errors;
- `401` for unauthenticated session state;
- `403` for authenticated-but-denied operations where confirming the resource is acceptable;
- `404` for absent or deliberately non-disclosed/invisible records;
- `409` where a real state conflict/idempotency contract requires it;
- `429` when rate limiting is active and exceeded;
- `5xx` only for genuine server/upstream failures, with secret-safe logging.

Validation responses should identify actionable fields without returning stack traces or secret
configuration.

## 26. Mutation rules

- PUT/PATCH semantics must be explicit per endpoint; partial updates should not accidentally apply
  create-only required-field validation.
- Writes happen in services/business transitions, not directly in serializers/views where the app
  conventions require service ownership.
- Idempotent actions/import/conversion operations should remain idempotent when retried.
- Soft-delete/restore rules follow the owning model/service rather than generic client assumptions.

## 27. API evolution rule

The API is allowed to evolve while HomeStack is pre-1.0 and household-owned, but changes must stay
coherent:

1. update URL/view/service tests;
2. update the owning node/core spec if the public contract changed;
3. update frontend client/types in the same feature change;
4. update this document only when a cross-cutting convention or major route family changes;
5. remove obsolete endpoints from docs rather than preserving misleading compatibility prose.