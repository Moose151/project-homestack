"""
Management command: seed_people

Creates placeholder Person records for dev/demo purposes.
Run once after initial setup; idempotent (skips existing display_names).

Usage:
    python manage.py seed_people

Generates 2 adults and 2 children with generic names per D15 (no household specifics).
Customise by editing the seed data below before running, or via Django admin after.
"""
from django.core.management.base import BaseCommand

from apps.core.models import get_active_household
from apps.people.models import Person

_SEED_PEOPLE = [
    {"display_name": "Adult 1", "profile_type": Person.ProfileType.ADULT, "colour": "#4A90E2"},
    {"display_name": "Adult 2", "profile_type": Person.ProfileType.ADULT, "colour": "#7B68EE"},
    {"display_name": "Child 1", "profile_type": Person.ProfileType.CHILD, "colour": "#50C878"},
    {"display_name": "Child 2", "profile_type": Person.ProfileType.CHILD, "colour": "#FFB347"},
]


class Command(BaseCommand):
    help = "Seed placeholder Person records (dev convenience — D15)."

    def handle(self, *args, **options):
        household = get_active_household()
        if not household:
            self.stderr.write("No active household found. Run migrations first.")
            return

        created = 0
        for data in _SEED_PEOPLE:
            _, was_created = Person.objects.get_or_create(
                household=household,
                display_name=data["display_name"],
                defaults={
                    "profile_type": data["profile_type"],
                    "colour": data["colour"],
                },
            )
            if was_created:
                created += 1
                self.stdout.write(f"  Created: {data['display_name']}")
            else:
                self.stdout.write(f"  Skipped (exists): {data['display_name']}")

        self.stdout.write(self.style.SUCCESS(f"Done. {created} person(s) created."))
