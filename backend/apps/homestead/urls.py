from django.urls import path

from apps.homestead.views import (
    ApplianceDetailView,
    ApplianceListView,
    HomesteadSearchView,
    HouseholdCostDetailView,
    HouseholdCostListView,
    ImprovementDetailView,
    ImprovementListView,
    InsurancePolicyDetailView,
    InsurancePolicyListView,
    MaintenanceCompleteView,
    MaintenanceCostView,
    MaintenanceDetailView,
    MaintenanceListView,
    PoolCareScheduleView,
    PoolDetailView,
    PoolListView,
    PoolStatusView,
    PropertyDetailView,
    PropertyListView,
    ProviderDetailView,
    ProviderListView,
    RoomDetailView,
    RoomItemDetailView,
    RoomItemListView,
    RoomListView,
    RoomProductDetailView,
    RoomProductListView,
    UtilityBillDetailView,
    UtilityBillListView,
    UtilityUsageView,
    WaterTestDetailView,
    WaterTestListView,
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
    path("maintenance/<int:task_id>/track-cost/", MaintenanceCostView.as_view(), name="homestead-maintenance-track-cost"),

    path("improvements/", ImprovementListView.as_view(), name="homestead-improvement-list"),
    path("improvements/<int:improvement_id>/", ImprovementDetailView.as_view(), name="homestead-improvement-detail"),

    path("rooms/", RoomListView.as_view(), name="homestead-room-list"),
    path("rooms/<int:room_id>/", RoomDetailView.as_view(), name="homestead-room-detail"),
    path("rooms/<int:room_id>/items/", RoomItemListView.as_view(), name="homestead-room-item-list"),
    path("rooms/<int:room_id>/items/<int:item_id>/", RoomItemDetailView.as_view(), name="homestead-room-item-detail"),
    path("rooms/<int:room_id>/items/<int:item_id>/products/", RoomProductListView.as_view(), name="homestead-room-product-list"),
    path("rooms/<int:room_id>/items/<int:item_id>/products/<int:product_id>/", RoomProductDetailView.as_view(), name="homestead-room-product-detail"),

    path("utility-bills/", UtilityBillListView.as_view(), name="homestead-utility-bill-list"),
    path("utility-bills/<int:bill_id>/", UtilityBillDetailView.as_view(), name="homestead-utility-bill-detail"),
    path("utility-usage/", UtilityUsageView.as_view(), name="homestead-utility-usage"),

    path("pools/", PoolListView.as_view(), name="homestead-pool-list"),
    path("pools/<int:pool_id>/", PoolDetailView.as_view(), name="homestead-pool-detail"),
    path("pools/<int:pool_id>/status/", PoolStatusView.as_view(), name="homestead-pool-status"),
    path("pools/<int:pool_id>/care-schedule/", PoolCareScheduleView.as_view(), name="homestead-pool-care-schedule"),
    path("pools/<int:pool_id>/water-tests/", WaterTestListView.as_view(), name="homestead-water-test-list"),
    path("pools/<int:pool_id>/water-tests/<int:test_id>/", WaterTestDetailView.as_view(), name="homestead-water-test-detail"),

    path("insurance/", InsurancePolicyListView.as_view(), name="homestead-insurance-list"),
    path("insurance/<int:policy_id>/", InsurancePolicyDetailView.as_view(), name="homestead-insurance-detail"),

    path("costs/", HouseholdCostListView.as_view(), name="homestead-cost-list"),
    path("costs/<int:cost_id>/", HouseholdCostDetailView.as_view(), name="homestead-cost-detail"),
]
