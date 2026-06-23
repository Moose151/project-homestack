# Document 4 — Database Design Document (DDD)

> Canonical. Supersedes all earlier DDD versions. Decisions D1–D18 in `00_README_and_Changelog.md`.

## 1. Purpose

Defines the PostgreSQL schema for HomeStack. The database supports a single household (with a
carried tenant column for future-proofing), users and people, central permissions, the node
registry, scheduling (calendar), notifications, attachments, search, audit, backups, and the
confirmed nodes.

## 2. Conventions

### 2.1 Base fields (all user-facing tables)
Via the `HouseholdBaseModel` (see Architecture §6), every user-facing table has:
`id`, `household_id`, `created_at`, `updated_at`, `created_by_id`, `updated_by_id`,
`deleted_at` (soft delete).

- `household_id` is present on every table but, in single-household mode, always points to the
  one seeded household. Carried deliberately (D1); never exposed in the UI.
- `created_by_id` / `updated_by_id` → **users** (ownership/audit).
- Record subjects/assignees → **people**, via explicit `*_person_id` fields (D12).

### 2.2 Dates, recurrence, calendar (D7, D8)
- Node records own their dates. The scheduling helper derives `calendar_events` from them and
  writes back `calendar_event_id`. Tables that surface on the calendar carry a nullable
  `calendar_event_id` rather than duplicating event fields.
- Recurrence is a single RRULE-style string on the owning record. No parallel `repeat_rule`
  formats; where a node needs recurrence it uses `recurrence_rule`.

### 2.3 Removed / deferred vs. earlier drafts
- **`event_bus_events`** table — **removed** for V1 (D4); decoupling uses signals.
- **`attachment_permissions`** ACL table — **deferred** (D11); attachments use
  `visibility` + `sensitivity`.
- **`search_index`** table — **removed** (D9); search uses Postgres FTS over live querysets.
  (A generated `tsvector` column may be added per searchable table instead.)
- Multi-household tables (signup/tenant management) — **not built**; one `households` row is
  seeded.

## 3. Core tables

### households
`id`, `name`, `slug`, `timezone`, `default_locale`, `created_at`, `updated_at`.
Exactly one active row in single-household mode.

### users
`id`, `household_id`, `display_name`, `username`, `email`, `avatar`, `pin_hash`,
`password_hash`, `role`, `is_active`, `is_child_account`, `colour`, `last_login_at`,
base fields.
PIN and password hashed with **Argon2id**. `role` ∈ {admin, manager, user, guest}.

### people
`id`, `household_id`, `linked_user_id` (nullable), `display_name`, `preferred_name`,
`avatar`, `colour`, `date_of_birth`, `profile_type` ∈ {adult, child, other}, `notes`,
base fields.
A person may have no login (`linked_user_id` null). People are the subjects/assignees across
nodes.

### roles
`id`, `household_id`, `name`, `description`, `is_system_role`, timestamps.

### permissions
`id`, `code`, `name`, `description`, `scope`, timestamps.

### role_permissions
`id`, `role_id`, `permission_id`, `created_at`.

### user_permissions
`id`, `user_id`, `permission_id`, `is_granted`, timestamps.
Per-user overrides consumed by the central resolver (Architecture §7).

## 4. Node registry

### nodes
`id`, `key`, `name`, `description`, `icon`, `is_core`, `is_enabled_by_default`,
`requires_setup`, `supports_kiosk`, `supports_sensitive_lock`, timestamps.
Keys: atlas, home_wiki, pets, education, inventory, assets, hearth, travel, projects, health,
meridian, solace.

### household_nodes
`id`, `household_id`, `node_id`, `is_enabled`, `is_hidden`, `requires_reauthentication`,
`display_order`, `custom_name`, `custom_icon`, timestamps.

### node_settings
`id`, `household_id`, `node_id`, `key`, `value_json`, timestamps.

## 5. Hub

### hub_widgets
`id`, `key`, `name`, `description`, `source_node_id`, `supports_kiosk`, timestamps.

### household_hub_widgets
`id`, `household_id`, `widget_id`, `is_enabled`, `display_order`, `size`, `settings_json`,
timestamps.

### user_hub_widgets
`id`, `user_id`, `widget_id`, `is_enabled`, `display_order`, `settings_json`, timestamps.

## 6. Scheduling (calendar)

> App/table prefix `scheduling`, not `calendar` (D16). Table names kept as `calendar_events`
> for readability; the Django app is `scheduling`.

### calendar_events
`id`, `household_id`, `title`, `description`, `start_at`, `end_at`, `is_all_day`, `timezone`,
`recurrence_rule`, `source_node_id`, `source_record_type`, `source_record_id`,
`created_by_id`, `assigned_to_person_id`, `colour`, `visibility`, `sensitivity`, `location`,
base fields.

Generated and kept in sync by the scheduling helper from owning node records. `source_*`
identifies the originating record so the helper can update/delete in step.

- `visibility` ∈ {private, household, role_restricted, user_restricted, sensitive}
- `sensitivity` ∈ {normal, financial, health, document, private}

### calendar_event_attendees
`id`, `calendar_event_id`, `person_id`, `response_status`, timestamps.

## 7. Notifications

### notifications
`id`, `household_id`, `user_id`, `person_id`, `title`, `message`, `notification_type`,
`source_node_id`, `source_record_type`, `source_record_id`, `due_at`, `read_at`,
`dismissed_at`, `priority`, timestamps.

## 8. Attachments (D11)

### attachments
`id`, `household_id`, `uploaded_by_id`, `filename`, `original_filename`, `file_path`,
`mime_type`, `file_size`, `checksum`, `linked_node_id`, `linked_record_type`,
`linked_record_id`, `visibility`, `sensitivity`, base fields.
Access via `visibility` + `sensitivity` through the central resolver. No per-row ACL table in
V1. Sensitive downloads audited.

## 9. Tags & categories

### tags
`id`, `household_id`, `name`, `colour`, timestamps.

### tag_links
`id`, `tag_id`, `linked_node_id`, `linked_record_type`, `linked_record_id`, `created_at`.

### categories
`id`, `household_id`, `node_id`, `name`, `colour`, `icon`, `display_order`, base fields.

## 10. Audit

### audit_logs
`id`, `household_id`, `user_id`, `action`, `target_node_id`, `target_record_type`,
`target_record_id`, `ip_address`, `user_agent`, `metadata_json`, `created_at`.
(No `search_index` table — see §2.3.)

## 11. Backups (D17)

### backups
`id`, `household_id`, `created_by_id`, `backup_type`, `file_path`, `file_size`, `checksum`,
`status`, `started_at`, `completed_at`, `error_message`, `metadata_json`.
`metadata_json` records the matching media-tarball path and the schema version so restore can
verify compatibility. Restore is a documented procedure (Architecture §16), not a table.

## 12–18. Node tables

The node table definitions (Atlas, Home Wiki, Pets, Education, Inventory, Assets, Hearth,
Travel, Projects, Health) carry over from the previous DDD **with these global adjustments**
applied uniformly:

1. All inherit the base fields via `HouseholdBaseModel` (§2.1).
2. Any field that previously duplicated a calendar event is replaced by a nullable
   `calendar_event_id` populated by the scheduling helper (§2.2). Node records keep their own
   semantic date(s) (e.g. `next_due_at`) as the source of truth.
3. Any per-node `repeat_rule` is renamed/normalised to `recurrence_rule` (RRULE).
4. Assignee/subject fields use `*_person_id`; ownership/audit uses the base `created_by`/
   `updated_by` users.

Representative examples (full set retained from prior DDD):

- **Atlas:** `atlas_notes`, `atlas_lists` (`list_type` ∈ todo/grocery/checklist/shopping/
  general), `atlas_list_items` (`assigned_to_person_id`, `completed_by_id` → user),
  `atlas_reminders` (`recurrence_rule`, `calendar_event_id`).
- **Home Wiki:** `wiki_pages` (`is_kiosk_safe`, `visibility`); `wiki_page_versions` deferred
  but schema-anticipated.
- **Pets:** `pets`, `pet_treatments` (`next_due_at` source of truth, `recurrence_rule`,
  `calendar_event_id`), `pet_appointments`, `pet_weight_logs`. *(No household-specific
  assumptions — D15.)*
- **Education:** `education_institutions`, `education_courses` (`person_id`),
  `education_assessments` (`assigned_to_person_id`, `calendar_event_id`), `education_events`.
- **Inventory:** `inventory_locations`, `inventory_items` (`low_stock_threshold`,
  `expiry_date`).
- **Assets:** `assets` (`asset_type` enum), `asset_maintenance_records`
  (`recurrence_rule`, `calendar_event_id`), `asset_documents`, `vehicle_details` (only when
  `asset_type = vehicle`).
- **Hearth:** `hearth_recipes`, `hearth_recipe_ingredients`, `hearth_meal_plans`
  (`assigned_to_person_id`, `calendar_event_id`).
- **Travel:** `travel_trips`, `travel_bookings` (`calendar_event_id`),
  `travel_packing_items` (`assigned_to_person_id`).
- **Projects:** `projects` (`owner_person_id`), `project_tasks` (`assigned_to_person_id`,
  `calendar_event_id`), `project_notes`.
- **Health:** `health_records`, `health_medications`, `health_appointments`
  (`calendar_event_id`, `sensitivity = health`). Built only after security maturation; all
  rows sensitive by default.

## 19. Meridian & Solace tables (D13, D14)

No `external_apps` / `integrations` tables — the iframe layer is not built. Instead, native
node tables are created when each is migrated:

- **Meridian (early):** tasks, task approvals, points ledger, rewards, reward requests,
  categories, achievements/streaks — rebuilt on shared Users/People, with reused reward logic.
- **Solace (after security):** bills, paydays, planned purchases, buckets/set-asides,
  subscriptions, payday-checklist items — rebuilt on shared services, `sensitivity =
  financial`, re-auth required, reused recurrence/checklist logic.

Each migration includes a one-time import script mapping the existing app's data onto these
tables and onto HomeStack users/people.

## 20. V1 database scope

Core: `households` (single row), `users`, `people`, `roles`, `permissions`,
`role_permissions`, `user_permissions`, `nodes`, `household_nodes`, `node_settings`,
`hub_widgets`, `household_hub_widgets`, `user_hub_widgets`, `calendar_events`,
`calendar_event_attendees`, `notifications`, `attachments`, `tags`, `tag_links`,
`categories`, `audit_logs`, `backups`.

Nodes in V1: Atlas tables, `wiki_pages`, Pets tables, Education tables, and the **native
Meridian** tables.

Later: Inventory, Assets, Hearth, Travel, Projects, Health, and **native Solace**.

Not created: `event_bus_events`, `attachment_permissions`, `search_index`, `external_apps`.
