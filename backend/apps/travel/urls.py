from django.urls import path

from apps.travel import views

urlpatterns = [
    path("trips/", views.TripListView.as_view()),
    path("trips/<int:trip_id>/", views.TripDetailView.as_view()),
    path("trips/<int:trip_id>/bookings/", views.BookingListView.as_view()),
    path("bookings/<int:booking_id>/", views.BookingDetailView.as_view()),
    path("ideas/", views.IdeaListView.as_view()),
    path("ideas/<int:idea_id>/", views.IdeaDetailView.as_view()),
    path("ideas/<int:idea_id>/convert/", views.IdeaConvertView.as_view()),
]
