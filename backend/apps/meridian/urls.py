from django.urls import path

from apps.meridian.views import (
    CategoryDetailView,
    CategoryListView,
    PointsView,
    RewardDetailView,
    RewardListView,
    RewardRequestApproveView,
    RewardRequestListView,
    CartCheckoutView,
    GoalContributeView,
    GoalDetailView,
    GoalListView,
    RewardRequestRejectView,
    RewardRequestView,
    RoutineCompleteView,
    RoutineDetailView,
    RoutineListView,
    TaskApproveView,
    TaskCompleteView,
    TaskDetailView,
    TaskListView,
    TaskRejectView,
    WishlistItemContributeView,
    WishlistItemDetailView,
    WishlistItemFulfillView,
    WishlistItemListView,
    WishlistRequestApproveView,
    WishlistRequestListView,
    WishlistRequestRejectView,
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

    # Routines
    path("routines/", RoutineListView.as_view(), name="meridian-routine-list"),
    path("routines/<int:routine_id>/", RoutineDetailView.as_view(), name="meridian-routine-detail"),
    path("routines/<int:routine_id>/complete/", RoutineCompleteView.as_view(), name="meridian-routine-complete"),

    # Group goals
    path("goals/", GoalListView.as_view(), name="meridian-goal-list"),
    path("goals/<int:goal_id>/", GoalDetailView.as_view(), name="meridian-goal-detail"),
    path("goals/<int:goal_id>/contribute/", GoalContributeView.as_view(), name="meridian-goal-contribute"),

    # Wishlist
    path("wishlist/", WishlistItemListView.as_view(), name="meridian-wishlist-list"),
    path("wishlist/<int:item_id>/", WishlistItemDetailView.as_view(), name="meridian-wishlist-detail"),
    path("wishlist/<int:item_id>/contribute/", WishlistItemContributeView.as_view(), name="meridian-wishlist-contribute"),
    path("wishlist/<int:item_id>/fulfill/", WishlistItemFulfillView.as_view(), name="meridian-wishlist-fulfill"),
    path("wishlist-requests/", WishlistRequestListView.as_view(), name="meridian-wishlist-request-list"),
    path("wishlist-requests/<int:request_id>/approve/", WishlistRequestApproveView.as_view(), name="meridian-wishlist-request-approve"),
    path("wishlist-requests/<int:request_id>/reject/", WishlistRequestRejectView.as_view(), name="meridian-wishlist-request-reject"),

    # Points
    path("points/", PointsView.as_view(), name="meridian-points"),

    # Rewards
    path("rewards/", RewardListView.as_view(), name="meridian-reward-list"),
    path("rewards/<int:reward_id>/", RewardDetailView.as_view(), name="meridian-reward-detail"),
    path("rewards/<int:reward_id>/request/", RewardRequestView.as_view(), name="meridian-reward-request"),
    path("rewards/checkout/", CartCheckoutView.as_view(), name="meridian-cart-checkout"),

    # Reward requests
    path("reward-requests/", RewardRequestListView.as_view(), name="meridian-reward-request-list"),
    path("reward-requests/<int:request_id>/approve/", RewardRequestApproveView.as_view(), name="meridian-reward-request-approve"),
    path("reward-requests/<int:request_id>/reject/", RewardRequestRejectView.as_view(), name="meridian-reward-request-reject"),
]
