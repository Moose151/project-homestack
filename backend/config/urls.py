"""
Root URL config. API is served under /api/v1/ (API Specification §1).
"""
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.meridian.views import KioskMeridianView


def health(_request):
    return JsonResponse(
        {"status": "ok", "service": "homestack-backend", "phase": "2.0"}
    )


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", health, name="health"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/people/", include("apps.people.urls")),
    path("api/v1/household/", include("apps.core.urls")),
    path("api/v1/nodes/", include("apps.nodes.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),
    path("api/v1/calendar/", include("apps.scheduling.urls")),
    path("api/v1/atlas/", include("apps.atlas.urls")),
    path("api/v1/meridian/", include("apps.meridian.urls")),
    path("api/v1/achievements/", include("apps.achievements.urls")),
    path("api/v1/kiosk/meridian/", KioskMeridianView.as_view(), name="kiosk-meridian"),
    path("api/v1/hub/", include("apps.hub.urls")),
    path("api/v1/backups/", include("apps.backups.urls")),
]
