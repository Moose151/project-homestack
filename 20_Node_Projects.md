# Node Spec — Projects

> Canonical. **Later node** (post-V1). Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose & philosophy

Manages larger household initiatives needing tasks, notes, planning, timelines, files or
budgets — keeping big efforts from scattering across Atlas, Calendar and Home Wiki. Answers:
*"What bigger household things are we working on?"* Absorbs would-be standalone nodes like
garden projects, party planning, moving house, renovations and large purchases.

## 2. Belongs / does not belong

**Belongs:** renovations, garden builds, party planning, moving house, garage organisation,
large-purchase planning, home improvement, room makeovers.
**Not:** simple lists → Atlas; permanent instructions → Home Wiki; financial set-asides →
Solace; assets created by a project → Assets; trip itineraries → Travel; rewarded tasks →
Meridian.

## 3. Key features

**Project** — title, description, status (idea/planning/active/paused/complete/cancelled),
category, start/target date, `owner_person_id`, visibility.
**Tasks** — title, description, `assigned_to_person`, `due_at`, status, priority,
`calendar_event_id`.
**Notes** — text, attachments, links.
**Timeline** — milestones, due dates, calendar events.
**Budget** (optional) — estimated/actual cost; Solace link (future).

## 4. Permissions

Household-visible or restricted; sensitive projects hidden; financial project details
restricted or linked to Solace.

## 5. Hub / Calendar / Notifications

Widgets: active projects · tasks due · upcoming milestones · recently updated. Calendar (via
helper): milestones, due dates, project tasks, review dates. Notifications: task due ·
milestone upcoming · project overdue · assigned task updated.

## 6. Events (signals)

Publishes: `project_created`, `project_task_created`, `project_task_completed`,
`project_milestone_due`, `project_completed`.
Consumes: `atlas_checklist_created`, `asset_created`, `solace_planned_purchase_created`.
Example: large-purchase project completed → `project_completed` → Assets prompts an asset
record; Solace closes the planned purchase (future).

## 7. Search / Kiosk

FTS over project names, tasks, notes, milestones, attachments. Not a primary child node; kiosk
may show assigned project tasks, a simple checklist, or a countdown — no complex boards by
default.

## 8. Data model

`projects` (`owner_person_id`), `project_tasks` (`assigned_to_person_id`, `calendar_event_id`),
`project_notes`. Inherit `HouseholdBaseModel`.

## 9. Scope & completion

Initial: project profiles · tasks · notes · attachments · calendar milestones · Hub widget ·
basic permissions. Complete when users create projects, add tasks/notes, attach documents,
track milestones, and show relevant items on Hub and Calendar. Future: Kanban boards, budget
integration, templates, photo progress, recurring reviews, Meridian/Assets integration.
