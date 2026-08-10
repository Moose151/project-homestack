from django.db import migrations


EXERCISES = [
    # name, type, muscle group, measurement
    ("Barbell bench press", "strength", "Chest", "reps_weight"),
    ("Incline dumbbell press", "strength", "Chest", "reps_weight"),
    ("Push-up", "strength", "Chest", "reps_only"),
    ("Cable fly", "strength", "Chest", "reps_weight"),
    ("Barbell back squat", "strength", "Legs", "reps_weight"),
    ("Front squat", "strength", "Legs", "reps_weight"),
    ("Leg press", "strength", "Legs", "reps_weight"),
    ("Walking lunge", "strength", "Legs", "reps_weight"),
    ("Leg extension", "strength", "Quadriceps", "reps_weight"),
    ("Leg curl", "strength", "Hamstrings", "reps_weight"),
    ("Standing calf raise", "strength", "Calves", "reps_weight"),
    ("Conventional deadlift", "strength", "Back", "reps_weight"),
    ("Romanian deadlift", "strength", "Hamstrings", "reps_weight"),
    ("Barbell row", "strength", "Back", "reps_weight"),
    ("Seated cable row", "strength", "Back", "reps_weight"),
    ("Lat pulldown", "strength", "Back", "reps_weight"),
    ("Pull-up", "strength", "Back", "reps_only"),
    ("Chin-up", "strength", "Back", "reps_only"),
    ("Overhead press", "strength", "Shoulders", "reps_weight"),
    ("Dumbbell shoulder press", "strength", "Shoulders", "reps_weight"),
    ("Lateral raise", "strength", "Shoulders", "reps_weight"),
    ("Face pull", "strength", "Shoulders", "reps_weight"),
    ("Barbell curl", "strength", "Biceps", "reps_weight"),
    ("Hammer curl", "strength", "Biceps", "reps_weight"),
    ("Triceps pushdown", "strength", "Triceps", "reps_weight"),
    ("Dips", "strength", "Triceps", "reps_only"),
    ("Hip thrust", "strength", "Glutes", "reps_weight"),
    ("Plank", "strength", "Core", "duration"),
    ("Hanging leg raise", "strength", "Core", "reps_only"),
    ("Running", "running", "Full body", "distance_time"),
    ("Treadmill running", "running", "Full body", "distance_time"),
    ("Walking", "cardio", "Full body", "distance_time"),
    ("Pool swimming", "swimming", "Full body", "distance_time"),
    ("Freestyle swimming", "swimming", "Full body", "distance_time"),
    ("Breaststroke swimming", "swimming", "Full body", "distance_time"),
    ("Open-water swimming", "swimming", "Full body", "distance_time"),
    ("Outdoor cycling", "cycling", "Legs", "distance_time"),
    ("Stationary bike", "cycling", "Legs", "duration"),
    ("Rowing machine", "cardio", "Full body", "distance_time"),
    ("Elliptical trainer", "cardio", "Full body", "duration"),
    ("Stair climber", "cardio", "Legs", "duration"),
    ("Jump rope", "cardio", "Full body", "duration"),
    ("Burpee", "cardio", "Full body", "reps_only"),
    ("Yoga", "mobility", "Full body", "duration"),
    ("Mobility session", "mobility", "Full body", "duration"),
]


def seed_forward(apps, schema_editor):
    Exercise = apps.get_model("fitness", "Exercise")
    Household = apps.get_model("core", "Household")
    household = Household.objects.order_by("id").first()
    if not household:
        return
    for name, exercise_type, muscle_group, measurement in EXERCISES:
        Exercise.objects.get_or_create(
            household=household, name=name,
            defaults={
                "exercise_type": exercise_type, "muscle_group": muscle_group,
                "measurement": measurement, "weight_unit": "kg", "distance_unit": "km",
                "is_system": True,
            },
        )


def seed_reverse(apps, schema_editor):
    apps.get_model("fitness", "Exercise").objects.filter(is_system=True, name__in=[row[0] for row in EXERCISES]).delete()


class Migration(migrations.Migration):
    dependencies = [("fitness", "0001_initial"), ("core", "0002_seed_household")]
    operations = [migrations.RunPython(seed_forward, seed_reverse)]

