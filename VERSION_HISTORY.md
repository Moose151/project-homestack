# HomeStack — Version History

> **Current version: 0.7.5**
>
> Versioning: `0.X` bumps mark major milestones (new node, significant new capability).
> `0.X.Y` bumps mark smaller additions within a milestone.
>
> **Rule:** bump the version and add a row here with every push to `main`.

---

## 0.7 — Node fleshing-out & shared UX parity

### 0.7.5 — 2026-07-19
- **Books**: the add-book form now suggests existing books as you type the title, so you can
  reuse a record instead of creating a duplicate; inputs and header moved onto the shared kit.

### 0.7.4 — 2026-07-19
- **Meridian** tasks gain a **weekly recurrence** picker (choose the weekdays a repeatable
  task re-arms on) in both the create and edit forms — the backend already stored/honoured
  the RRULE, but there was no way to set it. Repeating tasks now show a "↻ days" badge.
- _Remaining Meridian parity (follow-up): photo evidence on completions and importing legacy
  completion history._

### 0.7.3 — 2026-07-19
- **Education** gains an **Institutions** management tab (add / edit / delete schools and
  universities) and an **education-wide search box** (courses, assignments, classes) wired
  to the existing FTS endpoint.
- _Remaining Education parity (follow-up): a dedicated Education Events model (excursions /
  term dates / school events), plus notifications and outbound signals._

### 0.7.2 — 2026-07-19
- **Atlas** gains a full **Notes** surface (browse / create / inline edit / delete, with
  household-or-private visibility) — previously notes only appeared in search.
- **Create a list of any type** (to-do, grocery, shopping, checklist, general) from a picker
  instead of always making a to-do list; lists now lay out in a responsive two-column grid.
- Reminders form and empty states moved onto the shared kit.

### 0.7.1 — 2026-07-19
- **Calendar** UX pass: event modal rebuilt on the shared Modal/Field kit; per-source
  **layer toggles** and a **My events** filter; **household calendar defaults** (default
  view, week-start, time format) an admin can set, with each user's own choices still
  taking precedence; calmer empty states. New migration `core/0004`.

### 0.7.0 — 2026-07-19
- **Shared UI kit**: new reusable primitives (`Field`/`Input`/`Textarea`/`Select`, `Tabs`,
  `Modal`, `EmptyState`, `Badge`, `PageHeader`) so every node shares one visual language.
  Adopted across the Meridian, Atlas and Education tab bars, headers and inputs.
- **Hub**: three new widgets — **Quick add** (add a reminder or note from the Hub),
  **Notifications** summary (unread count + recent, web-only), and an opt-in ambient
  **Thought for the day**. New seed migration `hub/0007`.

---

## 0.6 — Books Node

### 0.6.3 — 2026-07-17
- Books can now be edited inline from any individual shelf category.
- Club book cards also expose the same edit action because club entries share the underlying book record.
- Editable fields: title, author, pages, genre, ISBN, and description.

### 0.6.2 — 2026-07-17
- Global web layout widened from a narrow centered column to a responsive full workspace (`max-width: 1600px`) so nodes use desktop real estate properly.
- Books page now uses wider desktop grids with side panels for shelf counts, club items, and up-next, while keeping stacked mobile layout.
- Added the Books accent colour to shared UI tokens.

### 0.6.1 — 2026-07-17
- Books page UX changed to tab navigation: top-level Individual / Book club tabs, then Backlog / Reading / Read tabs inside each view.
- Added a top add-book control that selects the destination shelf when adding.
- Each book now has a shelf dropdown that moves it between Backlog, Reading and Read.
- Personal backlog books can be added directly to a selected book club.

### 0.6.0 — 2026-07-17
- New Books node: personal shelves for backlog, currently reading, and history.
- Book details include title, author, pages, genre, ISBN, description, and cover URL.
- One user rating/note per book, reused across personal shelves and book club history.
- Book clubs: create/edit club name and colour, add/remove HomeStack users, and collaboratively add/remove/reorder books.
- Club books track backlog, currently reading, and history; history shows member ratings and club average.
- Up-next queue for clubs sits separately from the full backlog and can be ordered independently.
- Club books also appear on a member's personal shelves, highlighted by club colour, with a filter to hide club items.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (books `0001`, nodes `0004`, permissions `0015`).

---

## 0.5 — Education Node (M3)

### 0.5.2 — 2026-07-17
- User colour is now editable in the Users admin page (added colour picker to edit form; was previously read-only).
- Person name sync fix: linking an existing person to a user account now copies the user's display name to the person (previously only colour was copied, leaving persons stuck with their original name e.g. "admin").
- Education academic profile: institution field replaced with a free-text input + datalist autocomplete. Typing a new institution name creates it automatically on save; existing institutions still autocomplete.
- Settings page expanded: Household card (name + timezone), Stacks toggles (read-only for non-managers), Family colour (unchanged), and a new Meridian card (points label + group goals / wishlist requests / auto-end streaks toggles) — Meridian card only shows when the stack is enabled.

### 0.5.1 — 2026-07-17
- Assessment notes: per-assessment text notes (add, edit, delete) inline on the Assignments tab.
- Assessment files: file upload/download on each assessment (criteria PDFs, reference docs); stored in `MEDIA_ROOT/education/assessments/<id>/`; served via Django in dev, Docker `media_data` volume in prod.
- Auto-assignee: assignment form now pre-selects the logged-in user (fixed async `useEffect` sync).
- User profile self-edit: `PATCH /api/v1/auth/me/` lets any user change their own display name, colour, avatar, PIN, or password without admin access. Accessible via clicking the user panel in the sidebar.
- Display name → Person sync: renaming an account now also renames the linked Person record.
- Academic profile: per-person enrolment profile (institution, programme, credits required, graduation year, notes). GET auto-creates a blank profile so the tab never 404s.
- Course credit tracking: `credit_value` and `is_completed` fields on courses; profile view shows a live credit progress bar (current/required/percentage).
- Module bucketing: profile page groups courses into Current / Upcoming / Past based on start/end dates and completion state.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (education `0003` + `0004`).

### 0.5.0 — 2026-07-14
- Education node: institutions, courses (with colour, teacher, dates), assessments (due dates sync to Calendar via D7 CalendarSyncMixin), class sessions (weekly timetable via RRULE).
- Two Hub widgets: upcoming assessments and today's timetable.
- `EducationPage`: Assignments tab, Courses tab, Timetable tab — mobile-first responsive layout.
- `education.*` permissions seeded; `education.delete` is admin/manager only.

**Deploy note:** `docker exec homestack-backend python manage.py migrate` (permissions `0014`, hub `0006`, education `0001`).

---

## 0.4 — Meridian Cockpit Revisit

### 0.4.0 — 2026-07-10
- Task completion model (`MeridianTaskCompletion`): per-person submission/approve/reject history with review notes.
- Adult Meridian Overview tab: pending approvals, balances, recent activity.
- Task management table: filters, inline edit, hide/archive/delete, completion history.
- Shop/Rewards management: metrics, reward table with inline edit, stock management, pending request queue.
- Reports/history cockpit: completion history, points ledger, badge catalogue, leaderboard.
- Category management UI in Settings tab.
- Reward-category linking: `MeridianReward.category` FK + filter/display in shop.
- Allowance config UI/API: per-person weekly allowance amount and weekday, togglable, manager-only PATCH.

---

## 0.3 — Core Surfaces: Hub, Atlas, Calendar (M2.5)

### 0.3.0 — 2026-06-25
- Hub widget config: per-household enable/disable/order/size, per-user hide/reorder; "Customise" panel on the Hub page.
- Ambient clock Hub widget (kiosk-safe, client-side).
- Atlas FTS: Postgres `SearchVector`/`SearchQuery` in prod, `icontains` fallback on SQLite; `GET /atlas/search/?q=`.
- Atlas list items gain `due_at` and `quantity`; due-date badges and quantity prefix in the UI.
- Calendar core: month/week/day/agenda views; per-person colour coding + legend; `start`/`end`/`node`/`person` filter params.
- `CalendarPeek` popover in the shell header (next events, quick-add).
- Calendar event create/edit/delete modal; synced events read-only with "edit in node" note.
- `calendar_upcoming` Hub widget (web + kiosk).
- Kiosk restyle: warm paper tokens, kiosk Calendar surface (month/week/day/agenda).
- Web login user-tile flow (avatar picker → PIN); emoji account pictures stored in `User.avatar`.
- Enter/Exit kiosk buttons; hardware-keyboard PIN entry; admin-only price fields in shop/wishlist/goals.

---

## 0.2 — Native Meridian Full Port (M2) + User Management

### 0.2.0 — 2026-06-25
- User management admin page: create/edit/deactivate users, link to Person, role management, PIN/password reset, avatar emoji picker.
- Meridian full port: tasks (completion scope, hot bonus, archive, recurring), reward shop (stock, daily limits, cart/checkout), routines + streaks, group goals, wishlist (request/approve/fund/fulfill), points ledger (typed transactions, balance vs lifetime-earned), reward reservations/refunds.
- Cross-node achievements/badges: 15 seeded badges, `PersonBadge`, `AchievementCounter`; awarded via events bus (no Meridian imports).
- Notifications: `Notification` model, `GET /notifications/`, unread count; wired into Meridian approvals and badge awards.
- Scheduled management command (`meridian_run_scheduled`): weekly allowances, perfect-month routine badges.
- Meridian settings: `points_label`, `group_goals_enabled`, `wishlist_requests_enabled`, `auto_end_streaks`; `GET/PATCH /meridian/settings/`.
- Reports/leaderboard API: `GET /meridian/reports/`.
- Full Meridian data import command (`import_meridian`): categories, points ledger, routines, goals, wishlist, badges, allowances — idempotent by natural keys.
- Full web frontend: Tasks board, Shop, Routines, Goals, Wishlist, Leaderboard, Badges, admin Settings panel.
- Full kiosk: tap-to-complete tasks and routines (celebration), reward shop, goals/wishlist quick-contribute, my-badges strip.
- CSRF fix: `@ensure_csrf_cookie` on `GET /auth/me/` + client reads `csrftoken` cookie for unsafe requests.

---

## 0.1 — Walking Skeleton (M1)

### 0.1.1 — 2026-06-24
- Nodes registry: `Node` catalogue (12 seeded), `HouseholdNode` (enable/disable), `NodeSetting`; `GET /nodes/`, `POST /nodes/<key>/enable|disable/`, `PATCH /nodes/<key>/settings/`.
- `AuditLog` (append-only): `log_audit()` helper; `GET /audit-logs/`; login events wired.
- `CalendarEvent` model + `CalendarSyncMixin`; `sync_event_for`/`delete_event_for` helpers (D7 — nodes never write CalendarEvent directly); full Calendar CRUD API.
- Atlas node: `AtlasNote`, `AtlasList`, `AtlasListItem`, `AtlasReminder` (calendar sync); full CRUD + visibility filter; `events` signal bus (D4).
- Hub node: `HubWidget`, `HouseholdHubWidget`, `UserHubWidget`; `GET /hub/` and `GET /hub/kiosk/`; Atlas todo + reminder widgets seeded.
- Kiosk frontend: state machine (ambient → avatar select → PIN → dashboard → idle timeout); Avatar + PIN components; kiosk users endpoint (`AllowAny`).
- Backups: `Backup` model; `create_backup` (pg_dump + media tar, checksum, audit), `restore_backup`; streaming download; `docs/restore.md`.
- Web frontend: `LoginPage` (avatar tiles → PIN); `AppShell` (sidebar + mobile bottom nav, dark mode); `HubPage`, `AtlasPage` (lists/reminders), `CalendarPage` (grouped upcoming events).
- `HomeStackPermission.for_resource()` DRF factory; `permission_action` view attribute for method overrides.

### 0.1.0 — 2026-06-23
- Repo scaffold: `backend/ frontend/ docs/ docker/ scripts/ backups/`; `.env.example`; `docker-compose.yml` + `docker-compose.dev.yml` (3 services: postgres, backend, frontend; hot-reload bind mounts; `media_data` + `backup_data` volumes).
- Django project: split settings `config/settings/{base,dev,prod,test}.py`; 14 app skeletons (`core accounts people permissions nodes hub scheduling notifications attachments audit search backups events atlas`); DRF + argon2-cffi.
- `core.Household` (single-row tenant anchor) + idempotent seed migration; `HouseholdBaseModel` (abstract: household FK, soft-delete, created/updated-by-user); `HouseholdManager`.
- `accounts.User` (AbstractBaseUser + HouseholdBaseModel): `display_name`, `username`, `email`, `avatar`, `pin_hash`, `role`, `colour`; `PinBackend` + `PasswordBackend`; session auth endpoints (`pin-login`, `password-login`, `logout`, `me`, `reauth`).
- `people.Person` (HouseholdBaseModel): `linked_user` (nullable OneToOne), `display_name`, `preferred_name`, `avatar`, `colour`, `date_of_birth`, `profile_type`; full CRUD API.
- Permission spine: `Permission` catalogue, `Role` (4 system roles), `RolePermission`, `UserPermission` overrides; resolver; `HomeStackPermission` DRF class; 4 `people.*` permissions seeded with default matrix.
- Household settings endpoint: `GET/PATCH /household/`.
