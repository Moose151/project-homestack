"""
accounts permissions — DRF permission classes.

Phase 1.3 stub: IsAuthenticated is the only requirement on protected auth endpoints.
The full central resolver (D10) arrives in Phase 1.5 and replaces ad-hoc checks here.
"""
from rest_framework.permissions import IsAuthenticated  # noqa: F401 — re-exported for convenience
