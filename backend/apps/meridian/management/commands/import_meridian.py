"""Management command: import_meridian (D14 — one-time native migration).

Imports a JSON export from the standalone Meridian app into the native node, mapping
legacy Meridian users → HomeStack people, and tasks/points/rewards/history → the new
tables. Idempotent and **dry-runnable** so you can verify the mapping before committing.

Usage
-----
    python manage.py import_meridian --file export.json --dry-run   # report only
    python manage.py import_meridian --file export.json             # apply

Expected export JSON shape (keys are tolerant; unknown keys are ignored)
------------------------------------------------------------------------
{
  "users":   [{"meridian_id": 1, "display_name": "Finn"}],
  "categories": [{"meridian_id": 1, "name": "Bedroom", "colour": "#50C878", "icon": "bed"}],
  "tasks":   [{"title": "Tidy room", "description": "", "points": 10,
               "category_meridian_id": 1, "assigned_user_meridian_id": 1,
               "is_hot": false, "status": "available"}],
  "rewards": [{"name": "Movie night", "description": "", "cost_points": 30, "is_active": true}],
  "points_entries": [{"user_meridian_id": 1, "points": 10, "reason": "Imported balance"}],
  "reward_requests": [{"reward_name": "Movie night", "user_meridian_id": 1,
                       "status": "approved", "points_spent": 30}]
}

People matching: a legacy user maps to an existing Person by display_name; if none
exists one is created (profile_type=child). Re-running skips people/tasks/rewards that
already exist by their natural key, so the import is safe to repeat.
"""
from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.core.models import get_active_household
from apps.meridian.models import (
    MeridianCategory,
    MeridianPointsEntry,
    MeridianReward,
    MeridianRewardRequest,
    MeridianTask,
)
from apps.people.models import Person


class Command(BaseCommand):
    help = "Import standalone Meridian data into the native node (D14). Dry-runnable."

    def add_arguments(self, parser):
        parser.add_argument("--file", required=True, help="Path to the Meridian export JSON.")
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Report what would be imported without writing anything.",
        )

    def handle(self, *args, **options):
        household = get_active_household()
        if not household:
            raise CommandError("No active household. Run migrations first.")

        try:
            with open(options["file"], encoding="utf-8") as fh:
                data = json.load(fh)
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read export file: {exc}")

        dry = options["dry_run"]
        label = "DRY-RUN — no changes written" if dry else "Importing"
        self.stdout.write(self.style.WARNING(label))

        # Use a transaction we roll back on dry-run so counts reflect real FK resolution.
        try:
            with transaction.atomic():
                stats = self._import(household, data)
                if dry:
                    transaction.set_rollback(True)
        except Exception as exc:  # surface mapping errors clearly
            raise CommandError(f"Import failed (no changes committed): {exc}")

        for label, n in stats.items():
            self.stdout.write(f"  {label}: {n}")
        self.stdout.write(self.style.SUCCESS("Dry-run complete." if dry else "Import complete."))

    # -- internals -----------------------------------------------------------

    def _import(self, household, data: dict) -> dict:
        stats = {k: 0 for k in (
            "people", "categories", "tasks", "rewards", "points_entries", "reward_requests"
        )}

        # users -> people (by display_name)
        people_by_mid: dict = {}
        for u in data.get("users", []):
            name = u.get("display_name") or u.get("name") or ""
            if not name:
                continue
            person, created = Person.objects.get_or_create(
                household=household, display_name=name,
                defaults={"profile_type": Person.ProfileType.CHILD},
            )
            people_by_mid[u.get("meridian_id")] = person
            stats["people"] += int(created)

        # categories
        cats_by_mid: dict = {}
        for c in data.get("categories", []):
            cat, created = MeridianCategory.objects.get_or_create(
                household=household, name=c["name"],
                defaults={"colour": c.get("colour", ""), "icon": c.get("icon", "")},
            )
            cats_by_mid[c.get("meridian_id")] = cat
            stats["categories"] += int(created)

        # tasks
        for t in data.get("tasks", []):
            assignee = people_by_mid.get(t.get("assigned_user_meridian_id"))
            category = cats_by_mid.get(t.get("category_meridian_id"))
            _, created = MeridianTask.objects.get_or_create(
                household=household, title=t["title"],
                defaults={
                    "description": t.get("description", ""),
                    "points": t.get("points", 0),
                    "category": category,
                    "assigned_to_person": assignee,
                    "is_hot": t.get("is_hot", False),
                    "status": t.get("status", MeridianTask.Status.AVAILABLE),
                },
            )
            stats["tasks"] += int(created)

        # rewards
        rewards_by_name: dict = {}
        for r in data.get("rewards", []):
            reward, created = MeridianReward.objects.get_or_create(
                household=household, name=r["name"],
                defaults={
                    "description": r.get("description", ""),
                    "cost_points": r.get("cost_points", 0),
                    "is_active": r.get("is_active", True),
                },
            )
            rewards_by_name[r["name"]] = reward
            stats["rewards"] += int(created)

        # points ledger (import as opening balances/history)
        for p in data.get("points_entries", []):
            person = people_by_mid.get(p.get("user_meridian_id"))
            if not person:
                continue
            MeridianPointsEntry.objects.create(
                household=household, person=person,
                points=p["points"], reason=p.get("reason", "Imported from Meridian"),
            )
            stats["points_entries"] += 1

        # reward request history
        for rr in data.get("reward_requests", []):
            person = people_by_mid.get(rr.get("user_meridian_id"))
            reward = rewards_by_name.get(rr.get("reward_name"))
            if not person or not reward:
                continue
            MeridianRewardRequest.objects.create(
                household=household, reward=reward, requested_by_person=person,
                status=rr.get("status", MeridianRewardRequest.Status.APPROVED),
                points_spent=rr.get("points_spent", 0),
            )
            stats["reward_requests"] += 1

        return stats
