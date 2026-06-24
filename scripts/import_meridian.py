#!/usr/bin/env python
"""Thin wrapper for the one-time Meridian data import (D14).

The real logic lives in the Django management command so it has ORM access and is
covered by tests. This wrapper just bootstraps Django and forwards arguments, so the
import can be run from the repo root per the Development Roadmap (Milestone 2).

Examples
--------
    python scripts/import_meridian.py --file export.json --dry-run
    python scripts/import_meridian.py --file export.json

Or call the command directly inside the backend container:

    python manage.py import_meridian --file export.json --dry-run
"""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402

if __name__ == "__main__":
    call_command("import_meridian", *sys.argv[1:])
