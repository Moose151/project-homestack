"""nodes URL config."""
from django.urls import path

from apps.nodes import views

urlpatterns = [
    path("", views.NodeListView.as_view(), name="nodes-list"),
    path("<slug:node_key>/enable/", views.NodeEnableView.as_view(), name="nodes-enable"),
    path("<slug:node_key>/disable/", views.NodeDisableView.as_view(), name="nodes-disable"),
    path("<slug:node_key>/settings/", views.NodeSettingsView.as_view(), name="nodes-settings"),
]
