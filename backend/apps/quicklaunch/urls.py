from django.urls import path

from apps.quicklaunch import views

urlpatterns = [
    path("shortcuts/", views.ShortcutListView.as_view(), name="quicklaunch-shortcuts"),
    path("shortcuts/reorder/", views.ShortcutReorderView.as_view(), name="quicklaunch-reorder"),
    path("shortcuts/<uuid:public_id>/", views.ShortcutDetailView.as_view(), name="quicklaunch-shortcut-detail"),
    path("shortcuts/<uuid:public_id>/resolve/", views.ShortcutResolveView.as_view(), name="quicklaunch-resolve"),
    path("targets/", views.TargetCatalogueView.as_view(), name="quicklaunch-targets"),
]
