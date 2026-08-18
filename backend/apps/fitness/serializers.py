from decimal import Decimal

from rest_framework import serializers

from apps.fitness.models import (
    Exercise, PersonalRecord, ProgramAssignment, ProgramWorkout, SessionExercise,
    SessionSet, TrainingProgram, WorkoutExercise, WorkoutSession,
)


class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = ["id", "name", "exercise_type", "muscle_group", "measurement", "weight_unit", "distance_unit", "is_system", "is_archived", "notes", "created_at", "updated_at"]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]

    def validate_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter an exercise name.")
        return value.strip()


class WorkoutExerciseWriteSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    position = serializers.IntegerField(min_value=0, default=0)
    target_sets = serializers.IntegerField(min_value=1, max_value=100, default=3)
    target_reps = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    target_weight = serializers.DecimalField(max_digits=9, decimal_places=2, required=False, allow_null=True)
    target_duration_seconds = serializers.IntegerField(min_value=1, required=False, allow_null=True)
    target_distance = serializers.DecimalField(max_digits=9, decimal_places=3, required=False, allow_null=True)
    rest_seconds = serializers.IntegerField(min_value=0, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ProgramWorkoutWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160)
    position = serializers.IntegerField(min_value=0, default=0)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    exercises = WorkoutExerciseWriteSerializer(many=True, default=list)


class WorkoutExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = WorkoutExercise
        fields = ["id", "exercise", "position", "target_sets", "target_reps", "target_weight", "target_duration_seconds", "target_distance", "rest_seconds", "notes"]


class ProgramWorkoutSerializer(serializers.ModelSerializer):
    exercises = WorkoutExerciseSerializer(many=True, read_only=True)

    class Meta:
        model = ProgramWorkout
        fields = ["id", "name", "position", "notes", "exercises"]


class ProgramAssignmentSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.name", read_only=True)

    class Meta:
        model = ProgramAssignment
        fields = ["id", "person_id", "person_name", "is_active"]


class TrainingProgramReadSerializer(serializers.ModelSerializer):
    workouts = ProgramWorkoutSerializer(many=True, read_only=True)
    assignments = ProgramAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = TrainingProgram
        fields = ["id", "name", "description", "visibility", "is_archived", "workouts", "assignments", "created_at", "updated_at"]


class TrainingProgramWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=160, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=TrainingProgram._meta.get_field("visibility").choices, required=False)
    is_archived = serializers.BooleanField(required=False)
    person_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    workouts = ProgramWorkoutWriteSerializer(many=True, required=False)

    def validate(self, attrs):
        if not self.partial and not attrs.get("name", "").strip():
            raise serializers.ValidationError({"name": "Enter a program name."})
        return attrs


class SessionSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionSet
        fields = ["id", "position", "reps", "weight", "duration_seconds", "distance", "is_completed", "completed_at"]
        read_only_fields = ["id", "position", "completed_at"]


class SessionExerciseSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)
    sets = SessionSetSerializer(many=True, read_only=True)
    last_performance = serializers.SerializerMethodField()

    class Meta:
        model = SessionExercise
        fields = ["id", "exercise", "position", "status", "notes", "sets", "last_performance"]

    def get_last_performance(self, obj):
        """What this person last completed for the exercise — the source of the prefilled sets."""
        history = getattr(obj, "last_performance", None)
        if not history:
            return None
        return {
            "session_name": history["session_name"],
            "performed_at": history["performed_at"],
            "sets": [{
                "reps": row["reps"],
                "weight": None if row["weight"] is None else str(row["weight"]),
                "duration_seconds": row["duration_seconds"],
                "distance": str(row["distance"]),
            } for row in history["sets"]],
        }


class PersonalRecordSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.name", read_only=True)
    exercise_name = serializers.CharField(source="exercise.name", read_only=True)
    exercise_type = serializers.CharField(source="exercise.exercise_type", read_only=True)
    weight_unit = serializers.CharField(source="exercise.weight_unit", read_only=True)
    distance_unit = serializers.CharField(source="exercise.distance_unit", read_only=True)

    class Meta:
        model = PersonalRecord
        fields = ["id", "person_id", "person_name", "exercise_id", "exercise_name", "exercise_type", "kind", "value", "distance", "weight_unit", "distance_unit", "session_id", "achieved_at"]


class WorkoutSessionSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source="person.name", read_only=True)
    program_name = serializers.CharField(source="program.name", read_only=True, default="")
    exercises = SessionExerciseSerializer(many=True, read_only=True)
    personal_records = PersonalRecordSerializer(many=True, read_only=True)

    class Meta:
        model = WorkoutSession
        fields = ["id", "person_id", "person_name", "program_id", "program_name", "source_workout_id", "name", "status", "started_at", "finished_at", "duration_seconds", "total_reps", "total_volume", "notes", "visibility", "exercises", "personal_records", "created_at", "updated_at"]


class StartSessionSerializer(serializers.Serializer):
    person_id = serializers.IntegerField()
    workout_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=160, required=False, allow_blank=True)
    visibility = serializers.ChoiceField(choices=WorkoutSession._meta.get_field("visibility").choices, default="household")


class LogRunSerializer(serializers.Serializer):
    """Input for the quick run form.

    Pace is not accepted: it is distance over duration, and storing a third number that could
    disagree with the other two would only create a way for them to drift.
    """

    person_id = serializers.IntegerField()
    distance = serializers.DecimalField(max_digits=9, decimal_places=3, min_value=Decimal("0.001"))
    duration_seconds = serializers.IntegerField(min_value=1, max_value=24 * 3600)
    started_at = serializers.DateTimeField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    visibility = serializers.ChoiceField(
        choices=WorkoutSession._meta.get_field("visibility").choices, default="household",
    )


class AddSessionExerciseSerializer(serializers.Serializer):
    exercise_id = serializers.IntegerField()
    target_sets = serializers.IntegerField(min_value=1, max_value=100, default=1)
    notes = serializers.CharField(required=False, allow_blank=True, default="")

