# Node Spec — Education

> Canonical. **V1 node.** Global rules from `00_README_and_Changelog.md` apply.

## 1. Purpose

Education manages school, university and learning responsibilities for household members —
supporting both adults studying at university and children at school. Answers: *"What learning,
school or study responsibilities are coming up?"*

## 2. Philosophy

Covers structured learning. Handles simple school reminders and detailed university course
tracking alike, using progressive depth.

## 3. What belongs

University course lists; assignment/exam dates; weekly timetables; primary-school homework;
school excursions; reading logs; school sports days; term dates; permission slips; study notes
linked to a course.

## 4. What does NOT belong

General notes → Atlas (unless attached to a course). Rewarded homework tasks → Meridian (may
be *generated* from Education). Pure calendar-only events with no education context → Calendar
directly. Sensitive medical school records → Health/Documents.

## 5. Primary users

Admins/managers manage all education records. Adults manage their own university records.
Children see homework, reading, school events and simple kiosk education cards.

## 6. Key features

**Institutions** — name, type (school, university, TAFE, other), location, contact info, notes.

**Courses/subjects** — name, code, institution, `person_id` (the student), start/end date,
teacher/lecturer, description.

**Assessments** — title, type (homework, assignment, exam, quiz, reading, project, other),
course/subject, `assigned_to_person`, `due_at`, status, priority, description, attachments,
`calendar_event_id`.

**Education events** — excursions, school events, class events, exam sessions, term dates,
university milestones.

## 7. Permissions

Visibility depends on relationship: children see their own school items; parents/managers/
admins manage children's education; adults keep university records private or
household-visible. Enforced via the central resolver.

## 8. Hub integration

Widgets: homework due · assignments due · exam countdown · today's classes · school events ·
reading reminders · upcoming education deadlines.

Completion rule: this node is not "done" until its Hub widget rows are seeded with
`source_node` set, kiosk support declared per widget, and content is supplied through
permission-filtered selectors that the Hub service calls without cross-node model imports.

## 9. Calendar integration

Events for assignments, homework due dates, exams, class times, school events, excursions,
term dates, reading reminders — via the scheduling helper; recurrence (e.g. weekly classes) as
`recurrence_rule`.

## 10. Notifications

Homework/assignment due soon · exam upcoming · school event tomorrow · permission slip needed ·
reading-log reminder.

## 11. Events (signals)

Publishes: `assessment_created`, `assessment_due`, `assessment_completed`, `homework_created`,
`homework_completed`, `school_event_created`, `exam_scheduled`.
Consumes: `meridian_task_completed`, `calendar_event_updated`.
Example: homework added → `homework_created` → Meridian optionally creates a rewarded task.

## 12. Search

FTS over course names, assessment titles, homework descriptions, school-event titles, teacher/
lecturer names, notes, attachment metadata — permission-filtered.

## 13. Kiosk

Homework cards, reading reminders, assignment countdowns, simple completion buttons, school
events, today/tomorrow view. Children see simple, positive language.

## 14. Data model

`education_institutions`, `education_courses` (`person_id`), `education_assessments`
(`assigned_to_person_id`, `calendar_event_id`), `education_events` (`assigned_to_person_id`,
`calendar_event_id`). All inherit `HouseholdBaseModel`. Shared: attachments, calendar_events,
notifications, audit_logs.

## 15. V1 scope

Institutions · courses/subjects · assessments/homework · education events · calendar
integration · Hub widgets · kiosk homework view · attachments · basic permissions · FTS.

## 16. Future enhancements

Study timers · reading logs · grade tracking · assignment progress bars · term templates ·
Meridian task generation · university dashboard · school calendar import.

## 17. Completion criteria

Adults track university deadlines; children view homework/school events; education dates appear
on Calendar and Hub; kiosk homework cards work; Hub widget rows/selectors are shipped; permitted
records searchable.
