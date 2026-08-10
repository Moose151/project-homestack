# Document 6 — API Specification

> Canonical. Supersedes all earlier API docs. Decisions D1–D23 in `00_README_and_Changelog.md`.

## 1. Purpose & conventions

REST API for HomeStack. Base path `/api/v1/`.

- **Auth:** Django **session** auth (web/kiosk). Token auth added with native apps (D6).
- **Routes:** lowercase kebab-case.
- **Every endpoint** passes through the central layer and validates: authentication,
  household ownership, node-enabled status, role permission, record visibility,
  sensitive-node access, and re-authentication where required (D10).
- **No generic `/integrations/` or external-app endpoints** — Meridian and Solace are native
  nodes (D13), while Home Assistant has a dedicated `/home-assistant/` bridge contract (D22).
  No iframe layer or arbitrary service-call proxy is built.
- **No `/events/` endpoints** — the event interface is internal signals (D4).

## 2. Authentication

```
POST /api/v1/auth/pin-login/
POST /api/v1/auth/password-login/
POST /api/v1/auth/logout/
GET  /api/v1/auth/me/
POST /api/v1/auth/reauth/          # password-based; grants short-lived elevated state
```
Re-auth applies to: Solace, Health, sensitive Documents/Attachments (and optionally specific
Assets/People fields). *(No `/auth/refresh/` in V1 — that returns with token auth.)*

## 3. Core APIs

**Users**
```
GET   /api/v1/users/
POST  /api/v1/users/
GET   /api/v1/users/{user_id}/
PATCH /api/v1/users/{user_id}/
POST  /api/v1/users/{user_id}/disable/
POST  /api/v1/users/{user_id}/change-pin/
```

**Household** (single household)
```
GET   /api/v1/household/
PATCH /api/v1/household/
```

**People**
```
GET    /api/v1/people/
POST   /api/v1/people/
GET    /api/v1/people/{person_id}/
PATCH  /api/v1/people/{person_id}/
DELETE /api/v1/people/{person_id}/
```

**Permissions**
```
GET   /api/v1/permissions/me/
GET   /api/v1/permissions/roles/
PATCH /api/v1/permissions/roles/{role}/
```

**Nodes**
```
GET   /api/v1/nodes/
POST  /api/v1/nodes/{node_key}/enable/
POST  /api/v1/nodes/{node_key}/disable/
PATCH /api/v1/nodes/{node_key}/settings/
```

## 4. Hub & kiosk
```
GET   /api/v1/hub/
PATCH /api/v1/hub/widgets/
GET   /api/v1/kiosk/hub/
GET   /api/v1/kiosk/ambient/
```

## 5. Scheduling (calendar)
```
GET    /api/v1/calendar/events/
POST   /api/v1/calendar/events/
GET    /api/v1/calendar/events/{event_id}/
PATCH  /api/v1/calendar/events/{event_id}/
DELETE /api/v1/calendar/events/{event_id}/
GET    /api/v1/calendar/rotations/
POST   /api/v1/calendar/rotations/
GET    /api/v1/calendar/rotations/{schedule_id}/
PATCH  /api/v1/calendar/rotations/{schedule_id}/
DELETE /api/v1/calendar/rotations/{schedule_id}/
GET    /api/v1/calendar/rotation-occurrences/?start=YYYY-MM-DD&end=YYYY-MM-DD
PUT    /api/v1/calendar/rotations/{schedule_id}/exceptions/{date}/
DELETE /api/v1/calendar/rotations/{schedule_id}/exceptions/{date}/
```
Node-derived events are created/updated/deleted by the scheduling helper when their source
record changes (D7); direct event writes are for standalone calendar entries only.
Rotations use one anchored two-state pattern and are expanded for an end-exclusive date range
of at most 400 days (D23). `PUT` creates or replaces the single-day exception; `DELETE` restores
the repeating plan. These endpoints use the same `scheduling.*` permissions and visibility
filter as events.

## 6. Notifications
```
GET  /api/v1/notifications/
POST /api/v1/notifications/{notification_id}/read/
POST /api/v1/notifications/{notification_id}/dismiss/
```

## 7. Attachments
```
POST   /api/v1/attachments/
GET    /api/v1/attachments/
GET    /api/v1/attachments/{attachment_id}/download/
DELETE /api/v1/attachments/{attachment_id}/
```
Access via `visibility`/`sensitivity` (D11). Sensitive downloads audited.

## 8. Search
```
GET /api/v1/search/?q=term
```
Postgres FTS, permission-aware (D9).

## 9. Audit & backups
```
GET  /api/v1/audit-logs/
GET  /api/v1/backups/
POST /api/v1/backups/
GET  /api/v1/backups/{backup_id}/download/
POST /api/v1/backups/{backup_id}/restore/    # requires admin re-authentication
```

## 10. Atlas
```
GET/POST/GET/PATCH/DELETE  /api/v1/atlas/notes/[{note_id}/]
GET/POST/GET/PATCH/DELETE  /api/v1/atlas/lists/[{list_id}/]
POST   /api/v1/atlas/lists/{list_id}/items/
PATCH  /api/v1/atlas/list-items/{item_id}/
POST   /api/v1/atlas/list-items/{item_id}/complete/
POST   /api/v1/atlas/list-items/{item_id}/uncomplete/
DELETE /api/v1/atlas/list-items/{item_id}/
GET/POST/PATCH/DELETE       /api/v1/atlas/reminders/[{reminder_id}/]
```

## 11. Home Wiki
```
GET/POST/GET/PATCH/DELETE  /api/v1/wiki/pages/[{page_id}/]
GET/POST/PATCH/DELETE       /api/v1/wiki/categories/[{category_id}/]
POST /api/v1/wiki/pages/{page_id}/favourite/
POST /api/v1/wiki/pages/{page_id}/unfavourite/
GET  /api/v1/kiosk/wiki/
GET  /api/v1/kiosk/wiki/emergency/
```

## 12. Pets
```
GET/POST/GET/PATCH/DELETE  /api/v1/pets/[{pet_id}/]
GET/POST  /api/v1/pets/{pet_id}/treatments/
POST      /api/v1/pet-treatments/{treatment_id}/mark-done/
GET/POST  /api/v1/pets/{pet_id}/appointments/
PATCH/DELETE /api/v1/pet-appointments/{appointment_id}/
```

## 13. Education
```
GET/POST  /api/v1/education/institutions/
GET/POST  /api/v1/education/courses/
GET/POST  /api/v1/education/assessments/
PATCH     /api/v1/education/assessments/{assessment_id}/
POST      /api/v1/education/assessments/{assessment_id}/complete/
GET/POST/PATCH/DELETE  /api/v1/education/events/[{event_id}/]
```

## 14. Meridian (native — D13)
Migrated early; uses shared Users/People, scheduling, permissions.
```
GET/POST/GET/PATCH/DELETE  /api/v1/meridian/tasks/[{task_id}/]
POST   /api/v1/meridian/tasks/{task_id}/complete/
POST   /api/v1/meridian/tasks/{task_id}/approve/
POST   /api/v1/meridian/tasks/{task_id}/reject/
GET    /api/v1/meridian/points/                 # per-person ledger/summary
GET/POST  /api/v1/meridian/rewards/
POST   /api/v1/meridian/rewards/{reward_id}/request/
POST   /api/v1/meridian/reward-requests/{request_id}/approve/
GET    /api/v1/kiosk/meridian/                  # kid task/reward cards
```

## 15. Solace (native — D13; after security maturation)
Sensitive; re-auth required; hidden from children/users by default; access audited.
```
GET/POST/GET/PATCH/DELETE  /api/v1/solace/bills/[{bill_id}/]
POST   /api/v1/solace/bills/{bill_id}/paid/
GET/POST/PATCH/DELETE  /api/v1/solace/paydays/[{payday_id}/]
GET/POST/PATCH/DELETE  /api/v1/solace/purchases/[{purchase_id}/]
GET/POST/PATCH/DELETE  /api/v1/solace/buckets/[{bucket_id}/]
GET/POST/PATCH/DELETE  /api/v1/solace/subscriptions/[{subscription_id}/]
GET/POST/PATCH/DELETE  /api/v1/solace/checklist/[{item_id}/]
GET    /api/v1/solace/plan/                   # current pay-cycle transfer calculation
POST   /api/v1/solace/plan/checklist/         # idempotently generate cycle transfers
GET    /api/v1/solace/schedule/?start=&end=   # bill occurrences + expected income
POST   /api/v1/solace/occurrences/{id}/{paid|unpaid|skip}/
GET    /api/v1/solace/search/?q=
```

## 16. Homestead

The ordinary Homestead CRUD routes follow the node spec. Protected home-finance routes require
both Homestead and Solace permissions plus password re-authentication.

```
GET/POST/PATCH/DELETE /api/v1/homestead/maintenance/[{task_id}/]
POST /api/v1/homestead/maintenance/{task_id}/complete/
POST /api/v1/homestead/maintenance/{task_id}/track-cost/  # one linked Solace bill
GET/POST/PATCH/DELETE /api/v1/homestead/insurance/[{policy_id}/]
GET/POST/PATCH/DELETE /api/v1/homestead/costs/[{cost_id}/]
```

## 17. Home Assistant bridge (planned — D22/M5.5)

Backend-only credentials; endpoints never return the Home Assistant URL/token or arbitrary raw
attributes/service payloads. Full contract: `26_Node_Home_Assistant.md`.

```
GET  /api/v1/home-assistant/health/
POST /api/v1/home-assistant/health/test/
GET  /api/v1/home-assistant/entities/discover/
GET/POST/PATCH/DELETE /api/v1/home-assistant/entity-mappings/[{mapping_id}/]
GET  /api/v1/home-assistant/state/
GET/POST/PATCH/DELETE /api/v1/home-assistant/action-mappings/[{mapping_id}/]
POST /api/v1/home-assistant/actions/{action_id}/run/
GET/POST/PATCH/DELETE /api/v1/home-assistant/event-mappings/[{mapping_id}/]
POST /api/v1/home-assistant/event-mappings/{mapping_id}/test/
```

## 18. Later nodes
Inventory, Assets, Hearth, Travel, Projects, Health endpoints follow the same patterns as
their node specs (CRUD + node-specific actions), each behind the central permission layer.
Health is fully sensitive and re-auth-gated.

## 18.1 Fitness & training (D24)
```
GET/POST/PATCH/DELETE /api/v1/fitness/exercises/[{exercise_id}/]
GET/POST/PATCH/DELETE /api/v1/fitness/programs/[{program_id}/]
GET                       /api/v1/fitness/sessions/
POST                      /api/v1/fitness/sessions/start/
POST                      /api/v1/fitness/sessions/{session_id}/exercises/
PATCH                     /api/v1/fitness/session-sets/{set_id}/
POST                      /api/v1/fitness/session-exercises/{entry_id}/sets/
POST                      /api/v1/fitness/session-exercises/{entry_id}/drop/
POST                      /api/v1/fitness/sessions/{session_id}/{finish|abandon}/
GET                       /api/v1/fitness/records/
```
Fitness is social by default but supports private programs/sessions; it is not medical Health.
Session responses prefill each set's weight from the person's last completed training of that
exercise, and every session exercise carries a read-only `last_performance`
(`session_name`, `performed_at`, `sets`) naming where those defaults came from — `null` until the
exercise has visible history.

## 19. Standard error & response shape

Consistent envelope: list endpoints paginate; errors return a code + message + field errors.
401 for unauthenticated, 403 for permission/re-auth failures (with a `reauth_required` flag
where relevant so clients can prompt), 404 for not-found-or-not-visible (sensitive resources
return 404 rather than 403 to avoid confirming existence).
