"""Fitness and training models.

Templates describe future workouts; sessions snapshot them so historical training never changes
when a program is edited. People are workout subjects and Users remain audit owners (D12).
"""
from django.db import models

from apps.core.models import HouseholdBaseModel


class Visibility(models.TextChoices):
    PRIVATE = "private", "Private"
    HOUSEHOLD = "household", "Household"


class Exercise(HouseholdBaseModel):
    class Measurement(models.TextChoices):
        REPS_WEIGHT = "reps_weight", "Reps and weight"
        REPS_ONLY = "reps_only", "Reps"
        DURATION = "duration", "Time"
        DISTANCE_TIME = "distance_time", "Distance and time"

    class ExerciseType(models.TextChoices):
        STRENGTH = "strength", "Strength"
        RUNNING = "running", "Running"
        SWIMMING = "swimming", "Swimming"
        CYCLING = "cycling", "Cycling"
        CARDIO = "cardio", "Other cardio"
        MOBILITY = "mobility", "Mobility"
        SPORT = "sport", "Sport"

    name = models.CharField(max_length=160)
    exercise_type = models.CharField(max_length=20, choices=ExerciseType.choices)
    muscle_group = models.CharField(max_length=80, blank=True, default="")
    measurement = models.CharField(max_length=20, choices=Measurement.choices)
    weight_unit = models.CharField(max_length=10, blank=True, default="kg")
    distance_unit = models.CharField(max_length=10, blank=True, default="km")
    is_system = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["household", "name"], condition=models.Q(deleted_at__isnull=True),
                name="fitness_unique_active_exercise_name",
            )
        ]

    def __str__(self):
        return self.name


class TrainingProgram(HouseholdBaseModel):
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class ProgramWorkout(HouseholdBaseModel):
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name="workouts")
    name = models.CharField(max_length=160)
    position = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["position", "id"]


class ProgramAssignment(HouseholdBaseModel):
    program = models.ForeignKey(TrainingProgram, on_delete=models.CASCADE, related_name="assignments")
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="fitness_programs")
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["program", "person"], name="fitness_unique_program_person")]


class WorkoutExercise(HouseholdBaseModel):
    workout = models.ForeignKey(ProgramWorkout, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="workout_templates")
    position = models.PositiveSmallIntegerField(default=0)
    target_sets = models.PositiveSmallIntegerField(default=3)
    target_reps = models.PositiveSmallIntegerField(null=True, blank=True)
    target_weight = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    target_duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    target_distance = models.DecimalField(max_digits=9, decimal_places=3, null=True, blank=True)
    rest_seconds = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["position", "id"]


class WorkoutSession(HouseholdBaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        COMPLETED = "completed", "Completed"
        ABANDONED = "abandoned", "Abandoned"

    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="fitness_sessions")
    program = models.ForeignKey(TrainingProgram, null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions")
    source_workout = models.ForeignKey(ProgramWorkout, null=True, blank=True, on_delete=models.SET_NULL, related_name="sessions")
    name = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField()
    finished_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    total_reps = models.PositiveIntegerField(default=0)
    total_volume = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    notes = models.TextField(blank=True, default="")
    visibility = models.CharField(max_length=20, choices=Visibility.choices, default=Visibility.HOUSEHOLD)

    class Meta:
        ordering = ["-started_at"]


class SessionExercise(HouseholdBaseModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DROPPED = "dropped", "Dropped"

    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="exercises")
    exercise = models.ForeignKey(Exercise, on_delete=models.PROTECT, related_name="session_entries")
    source_template = models.ForeignKey(WorkoutExercise, null=True, blank=True, on_delete=models.SET_NULL, related_name="session_entries")
    position = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["position", "id"]


class SessionSet(HouseholdBaseModel):
    session_exercise = models.ForeignKey(SessionExercise, on_delete=models.CASCADE, related_name="sets")
    position = models.PositiveSmallIntegerField(default=0)
    reps = models.PositiveIntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=9, decimal_places=2, null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(null=True, blank=True)
    distance = models.DecimalField(max_digits=9, decimal_places=3, default=0)
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["position", "id"]


class PersonalRecord(HouseholdBaseModel):
    class Kind(models.TextChoices):
        MAX_WEIGHT = "max_weight", "Heaviest weight"
        ESTIMATED_1RM = "estimated_1rm", "Estimated one-rep max"
        MAX_REPS = "max_reps", "Most reps"
        FASTEST_TIME = "fastest_time", "Fastest time"
        LONGEST_DISTANCE = "longest_distance", "Longest distance"

    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="fitness_records")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="personal_records")
    session = models.ForeignKey(WorkoutSession, on_delete=models.CASCADE, related_name="personal_records")
    session_set = models.ForeignKey(SessionSet, on_delete=models.CASCADE, related_name="personal_records")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    value = models.DecimalField(max_digits=14, decimal_places=3)
    distance = models.DecimalField(max_digits=9, decimal_places=3, default=0)
    achieved_at = models.DateTimeField()

    class Meta:
        ordering = ["-achieved_at"]
        constraints = [models.UniqueConstraint(fields=["person", "exercise", "kind", "distance"], name="fitness_unique_current_record")]
