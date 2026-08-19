from django.urls import path

from apps.fitness import views

urlpatterns = [
    path("exercises/", views.ExerciseListView.as_view()),
    path("exercises/<int:exercise_id>/", views.ExerciseDetailView.as_view()),
    path("programs/", views.ProgramListView.as_view()),
    path("programs/<int:program_id>/", views.ProgramDetailView.as_view()),
    path("sessions/", views.SessionListView.as_view()),
    path("sessions/start/", views.SessionStartView.as_view()),
    path("sessions/log-run/", views.SessionLogRunView.as_view(), name="fitness-log-run"),
    path("sessions/<int:session_id>/", views.SessionDetailView.as_view()),
    path("sessions/<int:session_id>/exercises/", views.SessionAddExerciseView.as_view()),
    path("sessions/<int:session_id>/finish/", views.SessionFinishView.as_view()),
    path("sessions/<int:session_id>/abandon/", views.SessionAbandonView.as_view()),
    path("session-exercises/<int:entry_id>/drop/", views.SessionExerciseDropView.as_view()),
    path("session-exercises/<int:entry_id>/sets/", views.SessionExerciseAddSetView.as_view()),
    path("session-sets/<int:set_id>/", views.SessionSetDetailView.as_view()),
    path("records/", views.RecordListView.as_view()),
]

