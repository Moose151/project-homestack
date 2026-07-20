from django.urls import path

from apps.homestead.views import (
    ApplianceDetailView,
    ApplianceListView,
    HomesteadSearchView,
    ImprovementDetailView,
    ImprovementListView,
    MaintenanceCompleteView,
    MaintenanceDetailView,
    MaintenanceListView,
    PropertyDetailView,
    PropertyListView,
    ProviderDetailView,
    ProviderListView,
)

urlpatterns = [
    path("search/", HomesteadSearchView.as_view(), name="homestead-search"),

    path("properties/", PropertyListView.as_view(), name="homestead-property-list"),
    path("properties/<int:property_id>/", PropertyDetailView.as_view(), name="homestead-property-detail"),

    path("providers/", ProviderListView.as_view(), name="homestead-provider-list"),
    path("providers/<int:provider_id>/", ProviderDetailView.as_view(), name="homestead-provider-detail"),

    path("appliances/", ApplianceListView.as_view(), name="homestead-appliance-list"),
    path("appliances/<int:appliance_id>/", ApplianceDetailView.as_view(), name="homestead-appliance-detail"),

    path("maintenance/", MaintenanceListView.as_view(), name="homestead-maintenance-list"),
    path("maintenance/<int:task_id>/", MaintenanceDetailView.as_view(), name="homestead-maintenance-detail"),
    path("maintenance/<int:task_id>/complete/", MaintenanceCompleteView.as_view(), name="homestead-maintenance-complete"),

    path("improvements/", ImprovementListView.as_view(), name="homestead-improvement-list"),
    path("improvements/<int:improvement_id>/", ImprovementDetailView.as_view(), name="homestead-improvement-detail"),
]
