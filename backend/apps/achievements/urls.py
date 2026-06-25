from django.urls import path

from apps.achievements.views import BadgeListView, PersonBadgesView

urlpatterns = [
    path("badges/", BadgeListView.as_view(), name="achievements-badge-list"),
    path("my-badges/", PersonBadgesView.as_view(), name="achievements-person-badges"),
]
