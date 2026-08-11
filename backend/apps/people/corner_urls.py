from django.urls import path

from apps.people.corner_views import CornerDetailView, CornerReactionView

urlpatterns = [
    path("<int:person_id>/", CornerDetailView.as_view(), name="corner-detail"),
    path("<int:person_id>/reactions/", CornerReactionView.as_view(), name="corner-reaction"),
]
