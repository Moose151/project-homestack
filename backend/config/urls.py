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
    path("api/v1/search/", include("apps.search.urls")),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/users/", include("apps.accounts.user_urls")),
    path("api/v1/people/", include("apps.people.urls")),
    path("api/v1/corners/", include("apps.people.corner_urls")),
    path("api/v1/household/", include("apps.core.urls")),
    path("api/v1/nodes/", include("apps.nodes.urls")),
    path("api/v1/audit-logs/", include("apps.audit.urls")),
    path("api/v1/calendar/", include("apps.scheduling.urls")),
    path("api/v1/atlas/", include("apps.atlas.urls")),
    path("api/v1/meridian/", include("apps.meridian.urls")),
    path("api/v1/achievements/", include("apps.achievements.urls")),
    path("api/v1/education/", include("apps.education.urls")),
    path("api/v1/books/", include("apps.books.urls")),
    path("api/v1/wiki/", include("apps.home_wiki.urls")),
    path("api/v1/pets/", include("apps.pets.urls")),
    path("api/v1/homestead/", include("apps.homestead.urls")),
    path("api/v1/solace/", include("apps.solace.urls")),
    path("api/v1/fitness/", include("apps.fitness.urls")),
    path("api/v1/kiosk/meridian/", KioskMeridianView.as_view(), name="kiosk-meridian"),
    path("api/v1/hub/", include("apps.hub.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
    path("api/v1/attachments/", include("apps.attachments.urls")),
    path("api/v1/link-imports/", include("apps.link_imports.urls")),
    path("api/v1/backups/", include("apps.backups.urls")),
]
