"""Seed the badge catalogue (Milestone 2, Phase 2.14, D20).

The 15 badges ported from the standalone Meridian app. They are the first producer of a
cross-node system: other nodes register their own badges in later milestones with no changes
here. Awarding happens via the event handlers, not this migration.
"""
from django.db import migrations

_BADGES = [
    ("first_task", "First Task", "Completed your first approved task.", "✅"),
    ("five_tasks", "Task Starter", "Completed 5 approved tasks.", "⭐"),
    ("ten_tasks", "Task Champion", "Completed 10 approved tasks.", "🏆"),
    ("wishlist_saver", "Wishlist Saver", "Saved toward a wishlist item.", "🎁"),
    ("wishlist_funded", "Goal Reached", "Fully funded a wishlist item.", "🎯"),
    ("group_contributor", "Team Player", "Contributed to a group goal.", "🤝"),
    ("hundred_points_earned", "Big Earner", "Earned 100 points in total.", "💰"),
    ("routine_streak_3", "Getting Started", "Kept a routine going 3 days in a row.", "🔥"),
    ("routine_streak_7", "Week Warrior", "Kept a routine going 7 days in a row.", "⚡"),
    ("routine_streak_28", "Dedicated", "Kept a routine going 28 days in a row.", "💪"),
    ("routine_streak_30", "Monthly Champion", "Kept a routine going 30 days in a row.", "🏅"),
    ("routine_perfect_month", "Perfect Month", "Completed a routine every day of a month.", "📅"),
    ("routine_10", "Habit Forming", "Completed routines 10 times.", "🌱"),
    ("routine_50", "Routine Pro", "Completed routines 50 times.", "🌟"),
    ("routine_100", "Routine Master", "Completed routines 100 times.", "👑"),
]


def seed_forward(apps, schema_editor):
    Badge = apps.get_model("achievements", "Badge")
    for position, (code, name, description, icon) in enumerate(_BADGES):
        Badge.objects.get_or_create(
            code=code,
            defaults={
                "name": name, "description": description, "icon": icon,
                "source": "meridian", "position": position,
            },
        )


def seed_reverse(apps, schema_editor):
    Badge = apps.get_model("achievements", "Badge")
    Badge.objects.filter(code__in=[b[0] for b in _BADGES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("achievements", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_forward, seed_reverse),
    ]
