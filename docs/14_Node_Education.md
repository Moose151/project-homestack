# Node Spec — Education

> **Status:** shipped and in household use, with a mature university-first Study workflow plus
> support for broader school/learning records. Education owns structured study data; ordinary
> household notes remain Atlas and rewarded chores/tasks remain Meridian.

## 1. Purpose

Education answers: **What learning, course, assessment and school responsibilities are coming up,
and how is this Person's study organised?**

It supports detailed university study while leaving room for simpler school-age workflows without
forcing every student into the same level of tracking.

## 2. Ownership boundaries

**Education owns:**

- institutions;
- academic profile/program context;
- courses/subjects and completion/credit information;
- assessments/homework/exams and their education notes/files;
- class/timetable records;
- education/school events;
- Study/person-specific education views.

**Belongs elsewhere:**

- general non-course notes/to-dos → Atlas;
- rewarded household/homework incentive tasks → Meridian;
- calendar-only household event with no education owner → Calendar;
- medical school information → Health/shared protected Attachments;
- login/account management → Users/People core.

## 3. Student context

Opening **Study** resolves the signed-in User's linked Person first. Alphabetical Person ordering is
never identity.

A visible switcher can then move to another permitted household member. An unlinked User receives an
explicit choose/link-profile state rather than another Person's data being shown as "mine".

Assignments/courses are Person-subject records (D12), while create/update/review actors are Users.

## 4. Institutions

Institutions are saved household records used by Study/course/profile workflows rather than
repeated free-text names.

The UI uses saved Institution selectors and an **Add institution** path where appropriate. This
prevents duplicate spellings and lets contact/context improve later without rewriting every course.

## 5. Academic profile — shipped

A Person can have Education profile context such as:

- institution;
- programme/course-of-study name;
- credit requirements/defaults;
- graduation year;
- notes;
- derived current credit progress.

Credit totals are derived from completed course records rather than maintained as an independent
mutable counter.

The Study profile can group courses into useful current/upcoming/past/completed states according to
the implemented date/completion rules.

## 6. Courses / subjects — shipped

Courses can carry the implemented combination of:

- name/code;
- institution;
- Person/student;
- start/end dates;
- lecturer/teacher/context;
- description/notes;
- credit value;
- completion state.

Marking a course complete updates derived progress; it should not silently delete assessments or
history.

## 7. Assessments — shipped

Assessments cover relevant learning work such as assignments, homework, exams, quizzes, reading or
projects.

They can include the implemented combination of:

- title/type/course;
- assigned Person;
- due date;
- status/priority;
- description;
- notes;
- attached files;
- Calendar projection.

Assessment notes/files are Education-owned context; binary storage/security uses the shared file
boundary where applicable.

Completing an assessment preserves history and updates the owning Education record rather than
creating a second completed-task database in Atlas/Calendar.

## 8. Classes / timetable — shipped

Recurring class/session/timetable records remain Education-owned and use the established recurrence
and Calendar rules.

Weekly lecture/class context should be easy to scan in Study without forcing the user to manage the
same recurring date manually in Calendar.

## 9. Education events — shipped

Education events can cover school/university context such as excursions, school events, term
start/end, exam sessions, milestones, holidays/other education events according to current model
choices.

They sync/project through Calendar using D7 and retain Education ownership/deep links.

## 10. Calendar / Hub / Notifications

Education contributes permission-aware deadline/class/event information to Calendar and Hub.

Typical useful summaries include upcoming assessments/exams, today's classes and education events.

Notifications use the shared in-app/Web Push infrastructure. Assignment/event creation/completion
notifications remain source/Person/permission aware; Education does not implement a separate push
channel.

## 11. Permissions

Education visibility depends on the current Person/User relationship and central permissions.

Adults may manage their own study and permitted household education records. Children see only their
permitted learning information; managers/admins do not gain an ad-hoc bypass outside the central
resolver.

Private/restricted education notes/files remain filtered from Hub/Search/Calendar/kiosk projections.

## 12. Search

Search covers permitted institution/course/assessment/event/notes context according to current
selectors and FTS behavior.

Snippets are generated only after permission filtering.

## 13. Kiosk / mobile

Responsive web/phone Study is the current primary everyday surface.

Kiosk/child views can simplify to useful cards such as homework/deadline, classes/events and
positive completion actions where the relevant workflow is actually supported.

Do not claim unimplemented school-child features are complete merely because Education's university
workflow is mature.

## 14. Events and Meridian relationship

Education can publish meaningful assessment/class/event lifecycle events through D4.

A future or implemented rewarded-homework relationship with Meridian must remain opt-in and
source-linked: Education owns the assessment; Meridian owns the reward task. Do not merge the two
records or import Meridian models into Education.

## 15. Data ownership

Exact schema is defined by current Django models/migrations. Education owns the implemented
institution/profile/course/assessment/note/file/class/event families. Calendar, Hub, Search,
notifications and Corners are shared projections around the owning Education records.

## 16. Completion state

The current useful Education baseline is complete and materially beyond the original V1 outline:

- institution management;
- Person-aware Study routing;
- academic profile and credit progress;
- current/upcoming/past course grouping;
- course dates/credit/completion;
- assessments with notes/files;
- timetable/classes;
- education events;
- Calendar/Hub/search/notifications;
- responsive Study UI.

## 17. Future enhancements

Potential future work should be driven by actual school/uni use, for example:

- grades/marks and richer progress analytics;
- study timers;
- reading logs;
- term/import helpers;
- deeper school-age child/kiosk workflows;
- optional Meridian rewarded-homework handoff;
- external school/university calendar import.

A "university dashboard" is not a future blank requirement anymore—the current academic profile/
Study experience already fills that role and should be extended rather than duplicated.