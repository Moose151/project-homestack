from django.contrib import admin

from apps.fitness.models import (
    Exercise, PersonalRecord, ProgramAssignment, ProgramWorkout, SessionExercise,
    SessionSet, TrainingProgram, WorkoutExercise, WorkoutSession,
)

for model in (Exercise, TrainingProgram, ProgramWorkout, ProgramAssignment, WorkoutExercise,
              WorkoutSession, SessionExercise, SessionSet, PersonalRecord):
    admin.site.register(model)

