"""education models — institutions, courses, assessments, class sessions (Node Spec 14).

Milestone 3, uni-first V1 slice (owner re-prioritisation 2026-07-14): the models a
university student needs this term — courses/subjects, assignments/exams, and a weekly
lecture timetable. School-age-child features (homework cards, reading logs, kiosk) come
in a later slice.

All models inherit HouseholdBaseModel (household scoping, audit fields, soft-delete).
EducationAssessment and EducationClassSession implement CalendarSyncMixin so due dates and
weekly classes appear on the shared calendar without ever writing CalendarEvent rows
directly (D7). Weekly classes recur via `recurrence_rule` (RRULE, D8).
"""
from __future__ import annotations

import os

from django.db import models

from apps.core.models import AllObjectsManager, HouseholdBaseModel, HouseholdManager
from apps.scheduling.mixins import CalendarSyncMixin


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"
    ROLE_RESTRICTED = "role_restricted", "Role Restricted"
    SENSITIVE = "sensitive", "Sensitive"


class Sensitivity(models.TextChoices):
    NORMAL = "normal", "Normal"
    FINANCIAL = "financial", "Financial"
    HEALTH = "health", "Health"
    DOCUMENT = "document", "Document"
    PRIVATE = "private", "Private"


class EducationInstitution(HouseholdBaseModel):
    """A school, university, TAFE or other place of learning."""

    class InstitutionType(models.TextChoices):
        SCHOOL = "school", "School"
        UNIVERSITY = "university", "University"
        TAFE = "tafe", "TAFE"
        OTHER = "other", "Other"

    name = models.CharField(max_length=255)
    institution_type = models.CharField(
        max_length=20, choices=InstitutionType.choices, default=InstitutionType.UNIVERSITY
    )
    location = models.CharField(max_length=255, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education institution"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class EducationCourse(HouseholdBaseModel):
    """A course/subject a household member is studying."""

    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, blank=True, default="")
    institution = models.ForeignKey(
        EducationInstitution,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="courses",
    )
    student = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="education_courses",
    )
    teacher = models.CharField(max_length=255, blank=True, default="")  # teacher/lecturer
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    credit_value = models.PositiveSmallIntegerField(default=0)  # UOC / credits this course is worth
    is_completed = models.BooleanField(default=False)  # explicitly marked done; credits counted
    colour = models.CharField(max_length=20, blank=True, default="")
    description = models.TextField(blank=True, default="")
    is_archived = models.BooleanField(default=False)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education course"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.code} {self.name}".strip()


class EducationAssessment(CalendarSyncMixin, HouseholdBaseModel):
    """An assignment, exam, quiz, homework or other assessable item with a due date."""

    class AssessmentType(models.TextChoices):
        HOMEWORK = "homework", "Homework"
        ASSIGNMENT = "assignment", "Assignment"
        EXAM = "exam", "Exam"
        QUIZ = "quiz", "Quiz"
        READING = "reading", "Reading"
        PROJECT = "project", "Project"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        SUBMITTED = "submitted", "Submitted"
        DONE = "done", "Done"

    class Priority(models.TextChoices):
        LOW = "low", "Low"
        MEDIUM = "medium", "Medium"
        HIGH = "high", "High"

    title = models.CharField(max_length=255)
    assessment_type = models.CharField(
        max_length=20, choices=AssessmentType.choices, default=AssessmentType.ASSIGNMENT
    )
    course = models.ForeignKey(
        EducationCourse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assessments",
    )
    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="education_assessments",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=False)  # due on a date, no specific time
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.TODO
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    weight = models.CharField(max_length=50, blank=True, default="")  # e.g. "30%" of grade
    description = models.TextField(blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )
    sensitivity = models.CharField(
        max_length=20, choices=Sensitivity.choices, default=Sensitivity.NORMAL
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education assessment"
        ordering = ["due_at", "-updated_at"]

    def __str__(self) -> str:
        return self.title

    @property
    def is_complete(self) -> bool:
        return self.status in (self.Status.SUBMITTED, self.Status.DONE)

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.due_at:
            return None
        label = self.get_assessment_type_display()
        return {
            "title": f"{label}: {self.title}",
            "start_at": self.due_at,
            "is_all_day": self.is_all_day,
            "description": self.description,
            "visibility": self.visibility,
            "sensitivity": self.sensitivity,
            "colour": self.course.colour if self.course else "",
            "assigned_to_person_id": self.assigned_to_person_id,
        }

    def get_calendar_node_key(self) -> str:
        return "education"


class EducationAssessmentNote(HouseholdBaseModel):
    """A short note attached to an assessment — e.g. supervisor feedback, clarifications."""

    assessment = models.ForeignKey(
        EducationAssessment,
        on_delete=models.CASCADE,
        related_name="notes",
    )
    body = models.TextField()

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education assessment note"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"Note on {self.assessment_id} ({self.id})"


def _assessment_file_path(instance: "EducationAssessmentFile", filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return f"education/assessments/{instance.assessment_id}/{instance.id}{ext}"


class EducationAssessmentFile(HouseholdBaseModel):
    """A file attached to an assessment — e.g. the assignment brief/criteria PDF."""

    assessment = models.ForeignKey(
        EducationAssessment,
        on_delete=models.CASCADE,
        related_name="files",
    )
    label = models.CharField(max_length=255, blank=True, default="")
    file = models.FileField(upload_to=_assessment_file_path)
    original_filename = models.CharField(max_length=255, blank=True, default="")
    file_size = models.PositiveIntegerField(default=0)

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education assessment file"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.label or self.original_filename or f"File {self.id}"


class EducationClassSession(CalendarSyncMixin, HouseholdBaseModel):
    """A timetabled class/lecture, usually recurring weekly via `recurrence_rule` (D8)."""

    title = models.CharField(max_length=255, blank=True, default="")  # e.g. "Lecture", "Tutorial"
    course = models.ForeignKey(
        EducationCourse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="class_sessions",
    )
    student = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="education_class_sessions",
    )
    location = models.CharField(max_length=255, blank=True, default="")
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education class session"
        ordering = ["start_at"]

    def __str__(self) -> str:
        base = self.title or "Class"
        return f"{base} — {self.course}" if self.course_id else base

    @property
    def display_title(self) -> str:
        if self.course_id and self.course:
            label = self.course.code or self.course.name
            return f"{label} {self.title}".strip() if self.title else label
        return self.title or "Class"

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.start_at:
            return None
        return {
            "title": self.display_title,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "description": self.location,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "colour": self.course.colour if self.course else "",
            "assigned_to_person_id": self.student_id,
        }

    def get_calendar_node_key(self) -> str:
        return "education"


class EducationEvent(CalendarSyncMixin, HouseholdBaseModel):
    """A dated education event — excursion, school event, term date, exam session, milestone.

    Distinct from assessments (which have a due date + status) and class sessions (the weekly
    timetable): these are one-off or recurring calendar events that belong to school/uni life
    but are not assessable work. Syncs to the shared calendar via the helper only (D7); may
    recur via `recurrence_rule` (RRULE, D8) — e.g. a weekly assembly or fortnightly seminar.
    """

    class EventType(models.TextChoices):
        EXCURSION = "excursion", "Excursion"
        SCHOOL_EVENT = "school_event", "School event"
        TERM_START = "term_start", "Term start"
        TERM_END = "term_end", "Term end"
        EXAM_SESSION = "exam_session", "Exam session"
        MILESTONE = "milestone", "Milestone"
        HOLIDAY = "holiday", "Holiday"
        OTHER = "other", "Other"

    title = models.CharField(max_length=255)
    event_type = models.CharField(
        max_length=20, choices=EventType.choices, default=EventType.SCHOOL_EVENT
    )
    course = models.ForeignKey(
        EducationCourse,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    institution = models.ForeignKey(
        EducationInstitution,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="events",
    )
    assigned_to_person = models.ForeignKey(
        "people.Person",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="education_events",
    )
    start_at = models.DateTimeField()
    end_at = models.DateTimeField(null=True, blank=True)
    is_all_day = models.BooleanField(default=True)  # most school events are all-day
    location = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    recurrence_rule = models.CharField(max_length=512, blank=True, default="")
    calendar_event_id = models.PositiveBigIntegerField(null=True, blank=True)
    visibility = models.CharField(
        max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD
    )

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education event"
        ordering = ["start_at"]

    def __str__(self) -> str:
        return self.title

    # --- CalendarSyncMixin contract ---

    def get_calendar_data(self) -> dict | None:
        if not self.start_at:
            return None
        label = self.get_event_type_display()
        return {
            "title": f"{label}: {self.title}",
            "start_at": self.start_at,
            "end_at": self.end_at,
            "is_all_day": self.is_all_day,
            "description": self.description or self.location,
            "recurrence_rule": self.recurrence_rule,
            "visibility": self.visibility,
            "colour": self.course.colour if self.course else "",
            "assigned_to_person_id": self.assigned_to_person_id,
        }

    def get_calendar_node_key(self) -> str:
        return "education"


class EducationAcademicProfile(HouseholdBaseModel):
    """Per-person academic profile: institution enrolment, credit tracking, graduation goal.

    One profile per person (enforced at the service layer). Current credits are derived from
    completed `EducationCourse` rows for the person, so they update when courses are marked done.
    """

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="education_profile",
    )
    institution = models.ForeignKey(
        EducationInstitution,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="enrolled_profiles",
    )
    programme_name = models.CharField(max_length=255, blank=True, default="")  # e.g. "B Eng (CompSci)"
    credits_required = models.PositiveSmallIntegerField(default=0)  # total UOC to graduate
    credits_per_course_default = models.PositiveSmallIntegerField(default=6)  # UOC default when adding a new course
    graduation_year = models.PositiveSmallIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    objects = HouseholdManager()
    all_objects = AllObjectsManager()

    class Meta:
        verbose_name = "education academic profile"
        ordering = ["person__display_name"]

    def __str__(self) -> str:
        return f"Academic profile — {self.person}"

    def get_current_credits(self) -> int:
        """Sum of credit_value for completed courses assigned to this person."""
        from django.db.models import Sum
        result = (
            EducationCourse.objects.filter(student=self.person, is_completed=True)
            .aggregate(total=Sum("credit_value"))["total"]
        )
        return result or 0
