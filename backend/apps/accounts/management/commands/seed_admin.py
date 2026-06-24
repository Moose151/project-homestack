"""
Management command: seed_admin

Creates an admin User (avatar + PIN + password) and a linked Person in one step,
so a fresh deployment has a working login without dropping into a Django shell.

Idempotent: if a user with the given username already exists, nothing is changed.

Usage (flags):
    python manage.py seed_admin --username admin --display-name "Admin" \
        --pin 1234 --password "s3cret"

Usage (interactive — prompts for any flag not supplied; password is hidden):
    python manage.py seed_admin

PIN must be 4–6 digits (D6). Password is required for admin accounts (used for
sensitive re-auth and the Django admin panel).
"""
from getpass import getpass

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.people.models import Person


class Command(BaseCommand):
    help = "Create an admin user + linked person for a fresh deployment (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--username", help="Login handle (unique).")
        parser.add_argument("--display-name", help="Name shown in the UI, e.g. 'Admin'.")
        parser.add_argument("--pin", help="4–6 digit PIN.")
        parser.add_argument("--password", help="Full password (admin re-auth + admin panel).")
        parser.add_argument("--colour", default="#4A90E2", help="Hex accent colour.")

    def handle(self, *args, **options):
        household = get_active_household()
        if household is None:
            raise CommandError("No active household. Run `migrate` first to seed it.")

        username = options["username"] or input("Username: ").strip()
        if not username:
            raise CommandError("username is required.")

        if User.all_objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(
                f"User '{username}' already exists — nothing changed."
            ))
            return

        display_name = options["display_name"] or input("Display name: ").strip()
        if not display_name:
            raise CommandError("display_name is required.")

        pin = options["pin"] or getpass("PIN (4–6 digits): ").strip()
        if not (pin.isdigit() and 4 <= len(pin) <= 6):
            raise CommandError("PIN must be 4–6 digits.")

        password = options["password"] or getpass("Password: ")
        if not password:
            raise CommandError("Password is required for an admin account.")

        colour = options["colour"]

        user = User.objects.create_user(
            username=username,
            display_name=display_name,
            role=User.Role.ADMIN,
            password=password,
            colour=colour,
        )
        user.set_pin(pin)
        user.save()

        Person.objects.create(
            household=household,
            display_name=display_name,
            profile_type=Person.ProfileType.ADULT,
            linked_user=user,
            colour=colour,
            created_by=user,
            updated_by=user,
        )

        self.stdout.write(self.style.SUCCESS(
            f"Created admin '{username}' (+ linked person). You can log in on web and kiosk."
        ))
