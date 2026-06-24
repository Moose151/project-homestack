from django.urls import path

from apps.meridian.views import (
    CategoryDetailView,
    CategoryListView,
    PointsView,
    RewardDetailView,
    RewardListView,
    RewardRequestApproveView,
    RewardRequestListView,
    RewardRequestRejectView,
    RewardRequestView,
    TaskApproveView,
    TaskCompleteView,
    TaskDetailView,
    TaskListView,
    TaskRejectView,
)

urlpatterns = [
    # Tasks (API Spec §14)
    path("tasks/", TaskListView.as_view(), name="meridian-task-list"),
    path("tasks/<int:task_id>/", TaskDetailView.as_view(), name="meridian-task-detail"),
    path("tasks/<int:task_id>/complete/", TaskCompleteView.as_view(), name="meridian-task-complete"),
    path("tasks/<int:task_id>/approve/", TaskApproveView.as_view(), name="meridian-task-approve"),
    path("tasks/<int:task_id>/reject/", TaskRejectView.as_view(), name="meridian-task-reject"),

    # Categories
    path("categories/", CategoryListView.as_view(), name="meridian-category-list"),
    path("categories/<int:category_id>/", CategoryDetailView.as_view(), name="meridian-category-detail"),

    # Points
    path("points/", PointsView.as_view(), name="meridian-points"),

    # Rewards
    path("rewards/", RewardListView.as_view(), name="meridian-reward-list"),
    path("rewards/<int:reward_id>/", RewardDetailView.as_view(), name="meridian-reward-detail"),
    path("rewards/<int:reward_id>/request/", RewardRequestView.as_view(), name="meridian-reward-request"),

    # Reward requests
    path("reward-requests/", RewardRequestListView.as_view(), name="meridian-reward-request-list"),
    path("reward-requests/<int:request_id>/approve/", RewardRequestApproveView.as_view(), name="meridian-reward-request-approve"),
    path("reward-requests/<int:request_id>/reject/", RewardRequestRejectView.as_view(), name="meridian-reward-request-reject"),
]
