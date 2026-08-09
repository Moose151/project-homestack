# Node Spec — Home Assistant

> **Status:** Important planned node. Canonical implementation contract for Roadmap Milestone
> 5.5 and decision D22. This is a dedicated local bridge, not a generic integrations framework.

## 1. Purpose

The Home Assistant node brings useful smart-home state and a deliberately small set of safe
controls into HomeStack's Hub. It also lets approved HomeStack events drive Home Assistant
automations without asking either system to become the other's database.

The intended result is one calm household surface: family members can see whether selected
doors are open, rooms are comfortable, lights are on or household energy needs attention, while
Home Assistant continues doing the specialist work of device integration and automation.

## 2. Source-of-truth boundary

| Home Assistant owns | HomeStack owns |
|---|---|
| Devices, entities, areas and integrations | Household records, people and roles |
| Current device state and recorder history | Tasks, maintenance, insurance and finance records |
| Smart-home automations, scenes and scripts | Calendar data and record-level visibility |
| Device/service availability | Permissions, audit and HomeStack presentation mappings |

These boundaries are mandatory:

- HomeStack stores mappings and control policy, **not** a durable copy of all entity states or
  Home Assistant history.
- Home Assistant does not become the source of truth for Homestead, Solace, Atlas, Calendar or
  any other HomeStack node.
- A HomeStack record is entered once in its owning node. The bridge may emit a minimal event or
  expose a derived read-only sensor; it does not recreate that record in Home Assistant.
- Other HomeStack nodes publish through the D4 event interface and never import Home Assistant
  models or services directly.

## 3. Scope

### V1 — required

- Backend-only connection to one local Home Assistant installation.
- Admin discovery and explicit mapping of selected entities.
- Responsive Home Status page and permission-filtered Hub widget.
- Safe, allowlisted controls for selected low-risk entities/actions.
- Approved HomeStack domain events delivered to Home Assistant automations.
- Clear connected, stale, unavailable and permission-denied states.
- Phone, desktop and kiosk-aware layouts; kiosk access remains opt-in per mapping/action.

### Conditional follow-ups

- Home Assistant WebSocket subscription when measured REST polling is not responsive enough.
- A Home Assistant custom component only when native HomeStack sensors, calendar or to-do
  entities provide a proven household benefit.

### Explicitly out of scope for V1

- A generic integrations/plugin marketplace, arbitrary webhooks or an iframe of Home Assistant.
- Replacing Home Assistant dashboards, automations, recorder/history or device configuration.
- Mirroring every entity into PostgreSQL.
- Camera streaming or storage.
- Arbitrary service calls supplied by the browser.
- MQTT, Redis or Celery solely for this node.
- Remote cloud relay or public-internet exposure.

## 4. Architecture

The implementation is a normal opt-in node at `backend/apps/home_assistant` with the standard
models/serializers/views/urls/permissions/services/selectors/events/tasks/tests layering. Its
frontend route is `/home-assistant`; its API prefix is `/api/v1/home-assistant/`.

The server integrates with Home Assistant's supported APIs:

1. **REST first** for connection health, configuration, selected entity states, service discovery
   and allowlisted service calls.
2. **WebSocket only when justified** for live updates. A persistent connection runs as its own
   supervised management-command/service process, never as a forever loop in a web worker.
3. **Optional custom component last.** If needed, it lives in Home Assistant and talks only to a
   reviewed HomeStack API contract with a separate, narrowly scoped machine credential.

No browser receives the Home Assistant base URL or token. For V1, both are deployment
configuration, preferably injected as Docker secrets/environment variables (for example,
`HOMESTACK_HA_URL` and `HOMESTACK_HA_TOKEN`). The token is never stored in a user-facing model,
returned by an endpoint, written to a log or included in audit metadata.

## 5. Data model

Every persistent user-facing row inherits `HouseholdBaseModel` and uses the central visibility
rules.

### `HomeAssistantEntityMapping`

- `entity_id` — immutable Home Assistant entity identifier; unique per household.
- `label` — optional HomeStack-friendly label.
- `display_group`, `display_order` — Hub/Status grouping and ordering.
- `icon`, `colour` — optional presentation overrides.
- `visibility` — standard HomeStack record visibility.
- `kiosk_safe` — false by default for presence/security-related entities.
- `is_enabled` — hides the mapping without deleting its configuration.
- `is_controllable` — false by default; display permission is not control permission.

Current state, attributes, history and availability are fetched/derived and are not persisted on
this model.

### `HomeAssistantActionMapping`

- `name`, `description` — household-facing action text.
- `domain`, `service` — fixed server-reviewed Home Assistant service.
- `entity_mapping` — fixed permitted target.
- `service_data` — bounded, server-owned fields only; secrets prohibited.
- `requires_confirmation`, `requires_reauthentication`, `kiosk_safe`.
- `visibility`, `display_order`, `is_enabled`.

### `HomeAssistantEventMapping`

- `source_event` — approved D4 HomeStack event type.
- `target_event_type` — namespaced Home Assistant event, always prefixed `homestack_`.
- `payload_field_allowlist` — explicitly approved, non-sensitive fields.
- `is_enabled` and optional human-readable description.

Connection health, fetched state and delivery attempts are operational/ephemeral. Security-relevant
control and configuration actions use the existing audit system rather than a second log model.

## 6. Permissions and safety

Seed these central permissions:

- `home_assistant.view` — see permitted mapped state.
- `home_assistant.control` — run ordinary explicitly allowed actions.
- `home_assistant.configure` — manage connection tests, mappings and action/event policy.
- `home_assistant.sensitive_control` — run separately reviewed higher-risk actions after password
  re-authentication.

Admin/manager defaults may include view/control; configuration is admin-only by default. Children,
guests and kiosk get no control rights unless an individual action is explicitly marked safe and
the central resolver allows it.

Security requirements:

- Validate the configured URL at deployment and block unsafe redirects/rebinding. Prefer a fixed
  local address and verified HTTPS when the network supports it.
- Use short connect/read timeouts, bounded response sizes and a fixed Home Assistant API path.
- Redact `Authorization` headers and token-shaped values from logs, errors and diagnostics.
- Fetch only mapped entities for normal users. Discovery is admin-only and never auto-imports.
- Never accept arbitrary `domain`, `service`, `entity_id` or raw service payloads from the client;
  the browser submits only a HomeStack action-mapping ID plus permitted bounded inputs.
- Start controls with lights, switches, fans, scenes and reviewed scripts. Locks, alarm panels,
  garage doors/covers, cameras, sirens and safety equipment stay read-only or absent until a
  separate threat/safety review.
- Audit configuration changes and every control attempt/result with user, action mapping and
  outcome, but no access token or sensitive Home Assistant response body.

## 7. UI and Hub behaviour

### Home Status page

- Group selected entities by household meaning rather than exposing raw Home Assistant domains.
- Show friendly name, useful primary value, last-refresh age and clear unavailable/stale state.
- Keep controls secondary to status and require confirmation where consequences are not trivial.
- On phones, use one-column glanceable cards, large touch targets and no hover-only actions.
- On desktop, allow denser groups without shrinking targets below the shared design standard.
- Never expose raw attributes containing coordinates, camera URLs, access codes or diagnostic data.

### Hub widget

- Ship at least one `home_assistant_status` widget with the node, following the shared Hub widget
  pattern.
- Render a deliberately small summary: exceptions and attention first, then useful ambient values.
- Respect node enablement, `home_assistant.view`, record visibility, kiosk flags and user widget
  preferences before content is produced.
- Participate in existing Hub sizing and desktop drag-and-drop ordering; do not add another
  arrangement mechanism.

## 8. Event interactions

The node may consume approved events such as:

- `homestead.maintenance_completed` → fire a configured Home Assistant event for an announcement
  or dashboard refresh.
- `atlas.item_due` → fire a safe household reminder automation.
- `meridian.task_approved` → trigger a configured celebration scene.

Payloads carry stable HomeStack record links/IDs and the minimum useful display fields. They must
not include Solace amounts/account details, insurance policy numbers, private notes, health data,
tokens or unrestricted person data. Delivery runs after the owning transaction commits, uses a
short timeout and bounded immediate retry, records its outcome, and never fails the original node
write. It does not introduce a durable event-bus/replay table; a future durable retry mechanism
requires revisiting D4.

The node may publish connectivity/control-result events through the same interface, but no other
node may depend on Home Assistant being online for its own write to succeed.

## 9. API contract

Proposed V1 endpoints (all session-authenticated and centrally permissioned):

- `GET /api/v1/home-assistant/health/` — redacted connection state and last successful contact.
- `POST /api/v1/home-assistant/health/test/` — admin connection test; returns no credentials.
- `GET /api/v1/home-assistant/entities/discover/` — admin-only read-only discovery/search.
- `GET|POST /api/v1/home-assistant/entity-mappings/`
- `PATCH|DELETE /api/v1/home-assistant/entity-mappings/{id}/`
- `GET /api/v1/home-assistant/state/` — current permitted mapped state only.
- `GET|POST /api/v1/home-assistant/action-mappings/`
- `PATCH|DELETE /api/v1/home-assistant/action-mappings/{id}/`
- `POST /api/v1/home-assistant/actions/{id}/run/` — execute the stored allowlisted action.
- `GET|POST /api/v1/home-assistant/event-mappings/`
- `PATCH|DELETE /api/v1/home-assistant/event-mappings/{id}/`
- `POST /api/v1/home-assistant/event-mappings/{id}/test/` — admin-only safe test event.

Responses use normal HomeStack error envelopes. Upstream timeouts/unavailability map to a clear
`503`-class response; malformed mappings and disallowed controls are `400`/`403` as appropriate.

## 10. Availability and performance

- HomeStack remains fully usable when Home Assistant is offline, restarting or slow.
- Use a short in-process/request cache for mapped state and label its age. Never display stale data
  as live without an indicator.
- One slow/unavailable entity must not prevent other mapped state from rendering.
- Control calls do not claim success until Home Assistant accepts the service call; subsequent
  state reconciliation may still show a device-level failure.
- WebSocket reconnection, if added, uses exponential backoff, mapped-entity filtering and burst
  coalescing. Live state stays ephemeral.

## 11. Delivery milestones

The authoritative schedule and gates are Roadmap Milestone 5.5:

1. **5.5.0 Contract/security gate** — backend-only connection and failure-safe configuration.
2. **5.5.1 Read-only Home Status** — mappings, responsive page and Hub widget.
3. **5.5.2 Safe controls** — server allowlists, central permissions, confirmation and audit.
4. **5.5.3 HomeStack events into automations** — configured minimal event delivery and examples.
5. **5.5.4 Real-time state push (conditional)** — WebSocket only after measured need.
6. **5.5.5 Optional custom component** — native HA entities only after a credential/API decision.

Phases 5.5.0–5.5.3 constitute the important feature. The node is complete only when it is used
daily on phone/desktop, fails independently, leaks no unmapped/sensitive data, and neither system
duplicates ownership.

## 12. Test and acceptance checklist

- Permission tests are written before views; direct-ID, disabled-node, role and kiosk cases exist.
- Secrets never appear in browser bundles, API payloads, audit metadata, logs or exception text.
- SSRF/redirect, timeout, invalid-token, oversized-response and malformed-upstream cases fail safe.
- Only mapped entities are returned and sensitive attributes are filtered server-side.
- Tampered action IDs/fields, unapproved services/entities and stale sessions are rejected.
- Controls and mapping changes are audited; password re-auth is enforced where configured.
- Home Assistant offline/restart does not block Hub, Calendar, Homestead, Solace or login.
- Phone widths, desktop, keyboard navigation, screen-reader labels and kiosk-safe filtering are
  covered.
- No migration drift; no cross-node model import; no duplicate state/history/event-bus tables.

## 13. Protocol references

Implementation should be checked against current official Home Assistant developer documentation:

- REST API: <https://developers.home-assistant.io/docs/api/rest/>
- WebSocket API: <https://developers.home-assistant.io/docs/api/websocket/>
- Authentication and long-lived access tokens: <https://developers.home-assistant.io/docs/auth_api/>
- Custom integration file structure (conditional phase):
  <https://developers.home-assistant.io/docs/creating_integration_file_structure/>
