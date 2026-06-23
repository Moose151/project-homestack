"""
Root URL config. API is served under /api/v1/ (API Specification §1).

Per-app routers are included here as the apps gain endpoints (accounts/auth first,
Phase 1.3). For now only the health probe exists.
"""
from django.http import JsonResponse
from django.urls import path


def health(_request):
    return JsonResponse(
        {"status": "ok", "service": "homestack-backend", "phase": "1.1"}
    )


urlpatterns = [
    path("api/v1/health/", health, name="health"),
]
