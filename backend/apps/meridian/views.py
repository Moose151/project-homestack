"""meridian views — thin wrappers over selectors/services (Coding Standards §6).

Permission actions map to the resolver via HomeStackPermission:
  - default HTTP-method mapping for view/create/edit/delete;
  - 'approve' for approve/reject of tasks and reward requests (admin/manager);
  - 'complete' and 'request' for the two child-safe kiosk actions (narrow carve-out
    in the resolver — children may complete tasks and request rewards, nothing else).
"""
from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.meridian import selectors, services
from apps.meridian.serializers import (
    MeridianCategorySerializer,
    MeridianGroupGoalSerializer,
    MeridianPointsEntrySerializer,
    MeridianRewardRequestSerializer,
    MeridianRewardSerializer,
    MeridianRoutineSerializer,
    MeridianTaskSerializer,
    MeridianTaskWriteSerializer,
    MeridianWishlistItemSerializer,
    MeridianWishlistRequestSerializer,
    PointsSummarySerializer,
)
from apps.meridian.services import MeridianError
from apps.permissions.drf import HomeStackPermission

_Perm = HomeStackPermission.for_resource("meridian")


def _acting_person_id(request: Request, explicit: int | None) -> int | None:
    """Resolve which person an action is on behalf of.

    Admin/manager may pass an explicit person_id (acting on a child's behalf);
    otherwise fall back to the person linked to the acting user (kiosk self-service).
    """
    if explicit is not None:
        return explicit
    person = getattr(request.user, "person_profile", None)
    return person.id if person else None


def _domain_guard(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except MeridianError as exc:
        raise ValidationError({"detail": str(exc)})


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

class CategoryListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response(MeridianCategorySerializer(selectors.list_categories(), many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MeridianCategorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        category = services.create_category(request.user, **serializer.validated_data)
        return Response(MeridianCategorySerializer(category).data, status=status.HTTP_201_CREATED)


class CategoryDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_category(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, category_id: int) -> Response:
        category = self._get(category_id)
        serializer = MeridianCategorySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        category = services.update_category(request.user, category, **serializer.validated_data)
        return Response(MeridianCategorySerializer(category).data)

    def delete(self, request: Request, category_id: int) -> Response:
        services.delete_category(request.user, self._get(category_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        query = request.query_params.get("search")
        if query:
            return Response(MeridianTaskSerializer(
                selectors.search_meridian(request.user, query)["tasks"], many=True
            ).data)
        tasks = selectors.list_tasks(
            request.user,
            status=request.query_params.get("status") or None,
            hot_only=request.query_params.get("hot") == "1",
        )
        return Response(MeridianTaskSerializer(tasks, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MeridianTaskWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = services.create_task(request.user, **serializer.validated_data)
        return Response(MeridianTaskSerializer(task).data, status=status.HTTP_201_CREATED)


class TaskDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_task(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, task_id: int) -> Response:
        return Response(MeridianTaskSerializer(self._get(task_id)).data)

    def patch(self, request: Request, task_id: int) -> Response:
        task = self._get(task_id)
        serializer = MeridianTaskWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        task = services.update_task(request.user, task, **serializer.validated_data)
        return Response(MeridianTaskSerializer(task).data)

    def delete(self, request: Request, task_id: int) -> Response:
        services.delete_task(request.user, self._get(task_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class TaskCompleteView(APIView):
    """Child-safe action: a person marks a task done (pending approval)."""

    permission_classes = [_Perm]
    permission_action = "complete"

    def post(self, request: Request, task_id: int) -> Response:
        task = selectors.get_task(task_id)
        if task is None:
            raise NotFound()
        person_id = _acting_person_id(request, request.data.get("person_id"))
        task = services.complete_task(request.user, task, person_id=person_id)
        return Response(MeridianTaskSerializer(task).data)


class TaskApproveView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, task_id: int) -> Response:
        task = selectors.get_task(task_id)
        if task is None:
            raise NotFound()
        task = _domain_guard(services.approve_task, request.user, task)
        return Response(MeridianTaskSerializer(task).data)


class TaskRejectView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, task_id: int) -> Response:
        task = selectors.get_task(task_id)
        if task is None:
            raise NotFound()
        task = _domain_guard(
            services.reject_task, request.user, task, reason=request.data.get("reason", "")
        )
        return Response(MeridianTaskSerializer(task).data)


# ---------------------------------------------------------------------------
# Routines
# ---------------------------------------------------------------------------

class RoutineListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        person_id = _acting_person_id(request, request.query_params.get("person_id"))
        routines = selectors.list_routines(
            request.user, person_id=person_id,
            active_only=request.query_params.get("active") == "1",
        )
        return Response(MeridianRoutineSerializer(routines, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MeridianRoutineSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        routine = services.create_routine(request.user, **serializer.validated_data)
        return Response(MeridianRoutineSerializer(routine).data, status=status.HTTP_201_CREATED)


class RoutineDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_routine(pk)
        if obj is None:
            raise NotFound()
        return obj

    def patch(self, request: Request, routine_id: int) -> Response:
        routine = self._get(routine_id)
        serializer = MeridianRoutineSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        routine = services.update_routine(request.user, routine, **serializer.validated_data)
        return Response(MeridianRoutineSerializer(routine).data)

    def delete(self, request: Request, routine_id: int) -> Response:
        services.delete_routine(request.user, self._get(routine_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoutineCompleteView(APIView):
    """Child-safe action: a person completes a routine (immediate points, no approval)."""

    permission_classes = [_Perm]
    permission_action = "complete"

    def post(self, request: Request, routine_id: int) -> Response:
        routine = selectors.get_routine(routine_id)
        if routine is None:
            raise NotFound()
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to complete on behalf of."})
        _domain_guard(services.complete_routine, request.user, routine, person_id=person_id)
        # Return the routine with fresh per-person streak/done-today context.
        routine.streak = services.current_streak(routine, person_id)
        routine.done_today = services.completed_today(routine, person_id)
        return Response(MeridianRoutineSerializer(routine).data)


# ---------------------------------------------------------------------------
# Group goals
# ---------------------------------------------------------------------------

class GoalListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        goals = selectors.list_goals(active_only=request.query_params.get("active") == "1")
        return Response(MeridianGroupGoalSerializer(goals, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MeridianGroupGoalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        goal = services.create_goal(request.user, **serializer.validated_data)
        return Response(MeridianGroupGoalSerializer(goal).data, status=status.HTTP_201_CREATED)


class GoalDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_goal(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, goal_id: int) -> Response:
        return Response(MeridianGroupGoalSerializer(self._get(goal_id)).data)

    def patch(self, request: Request, goal_id: int) -> Response:
        goal = self._get(goal_id)
        serializer = MeridianGroupGoalSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        goal = services.update_goal(request.user, goal, **serializer.validated_data)
        return Response(MeridianGroupGoalSerializer(goal).data)

    def delete(self, request: Request, goal_id: int) -> Response:
        services.delete_goal(request.user, self._get(goal_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class GoalContributeView(APIView):
    """Child-safe action: a person contributes points to a group goal."""

    permission_classes = [_Perm]
    permission_action = "contribute"

    def post(self, request: Request, goal_id: int) -> Response:
        goal = selectors.get_goal(goal_id)
        if goal is None:
            raise NotFound()
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to contribute on behalf of."})
        try:
            amount = int(request.data.get("amount", 0))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "amount must be a number."})
        _domain_guard(services.contribute_to_goal, request.user, goal, person_id=person_id, amount=amount)
        return Response(MeridianGroupGoalSerializer(goal).data)


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------

class WishlistItemListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        person_id = request.query_params.get("person_id") or None
        items = selectors.list_wishlist_items(person_id=person_id, active_only=True)
        return Response(MeridianWishlistItemSerializer(items, many=True).data)

    def post(self, request: Request) -> Response:
        # Admin/manager adds an item directly (create permission).
        data = request.data
        item = services.create_wishlist_item(
            request.user,
            person_id=data.get("person_id"),
            name=(data.get("name") or "").strip(),
            point_cost=int(data.get("point_cost") or 0),
            description=data.get("description", ""),
            price_estimate=data.get("price_estimate", ""),
            store_url=data.get("store_url", ""),
            image_url=data.get("image_url", ""),
        )
        return Response(MeridianWishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)


class WishlistItemDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_wishlist_item(pk)
        if obj is None:
            raise NotFound()
        return obj

    def delete(self, request: Request, item_id: int) -> Response:
        services.delete_wishlist_item(request.user, self._get(item_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class WishlistItemContributeView(APIView):
    """Child-safe action: a person saves points toward their wishlist item."""

    permission_classes = [_Perm]
    permission_action = "contribute"

    def post(self, request: Request, item_id: int) -> Response:
        item = selectors.get_wishlist_item(item_id)
        if item is None:
            raise NotFound()
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to contribute on behalf of."})
        try:
            amount = int(request.data.get("amount", 0))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "amount must be a number."})
        _domain_guard(services.contribute_to_wishlist, request.user, item, person_id=person_id, amount=amount)
        return Response(MeridianWishlistItemSerializer(item).data)


class WishlistItemFulfillView(APIView):
    permission_classes = [_Perm]
    permission_action = "edit"

    def post(self, request: Request, item_id: int) -> Response:
        item = selectors.get_wishlist_item(item_id)
        if item is None:
            raise NotFound()
        item = services.fulfill_wishlist_item(request.user, item)
        return Response(MeridianWishlistItemSerializer(item).data)


class WishlistRequestListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        reqs = selectors.list_wishlist_requests(status=request.query_params.get("status") or None)
        return Response(MeridianWishlistRequestSerializer(reqs, many=True).data)

    def get_permission_action(self, request) -> str:
        # GET = view (list requests, manager); POST = request (child-safe).
        return "request" if request.method == "POST" else "view"

    def post(self, request: Request) -> Response:
        # Child-safe: a person requests an item for their wishlist.
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to request on behalf of."})
        serializer = MeridianWishlistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = services.request_wishlist_item(
            request.user, person_id=person_id,
            requested_name=serializer.validated_data["requested_name"],
            requested_description=serializer.validated_data.get("requested_description", ""),
        )
        return Response(MeridianWishlistRequestSerializer(req).data, status=status.HTTP_201_CREATED)


class WishlistRequestApproveView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, request_id: int) -> Response:
        req = selectors.get_wishlist_request(request_id)
        if req is None:
            raise NotFound()
        try:
            point_cost = int(request.data.get("point_cost", 0))
        except (TypeError, ValueError):
            raise ValidationError({"detail": "point_cost must be a number."})
        item = _domain_guard(
            services.approve_wishlist_request, request.user, req, point_cost=point_cost,
            description=request.data.get("description", ""),
            price_estimate=request.data.get("price_estimate", ""),
            store_url=request.data.get("store_url", ""),
            image_url=request.data.get("image_url", ""),
        )
        return Response(MeridianWishlistItemSerializer(item).data, status=status.HTTP_201_CREATED)


class WishlistRequestRejectView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, request_id: int) -> Response:
        req = selectors.get_wishlist_request(request_id)
        if req is None:
            raise NotFound()
        req = _domain_guard(
            services.reject_wishlist_request, request.user, req,
            reason=request.data.get("reason", ""),
        )
        return Response(MeridianWishlistRequestSerializer(req).data)


# ---------------------------------------------------------------------------
# Points
# ---------------------------------------------------------------------------

class PointsView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        return Response({
            "summary": PointsSummarySerializer(selectors.points_summary(), many=True).data,
            "entries": MeridianPointsEntrySerializer(
                selectors.list_points_entries(
                    person_id=request.query_params.get("person_id") or None
                ),
                many=True,
            ).data,
        })


# ---------------------------------------------------------------------------
# Rewards
# ---------------------------------------------------------------------------

class RewardListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        rewards = selectors.list_rewards(active_only=request.query_params.get("active") == "1")
        return Response(MeridianRewardSerializer(rewards, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = MeridianRewardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward = services.create_reward(request.user, **serializer.validated_data)
        return Response(MeridianRewardSerializer(reward).data, status=status.HTTP_201_CREATED)


class RewardDetailView(APIView):
    permission_classes = [_Perm]

    def _get(self, pk: int):
        obj = selectors.get_reward(pk)
        if obj is None:
            raise NotFound()
        return obj

    def get(self, request: Request, reward_id: int) -> Response:
        return Response(MeridianRewardSerializer(self._get(reward_id)).data)

    def patch(self, request: Request, reward_id: int) -> Response:
        reward = self._get(reward_id)
        serializer = MeridianRewardSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        reward = services.update_reward(request.user, reward, **serializer.validated_data)
        return Response(MeridianRewardSerializer(reward).data)

    def delete(self, request: Request, reward_id: int) -> Response:
        services.delete_reward(request.user, self._get(reward_id))
        return Response(status=status.HTTP_204_NO_CONTENT)


class RewardRequestView(APIView):
    """Child-safe action: a person requests to redeem a reward."""

    permission_classes = [_Perm]
    permission_action = "request"

    def post(self, request: Request, reward_id: int) -> Response:
        reward = selectors.get_reward(reward_id)
        if reward is None:
            raise NotFound()
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to request on behalf of."})
        req = _domain_guard(services.request_reward, request.user, reward, person_id=person_id)
        return Response(
            MeridianRewardRequestSerializer(req).data, status=status.HTTP_201_CREATED
        )


class CartCheckoutView(APIView):
    """Child-safe action: request several rewards at once (cart checkout)."""

    permission_classes = [_Perm]
    permission_action = "request"

    def post(self, request: Request) -> Response:
        person_id = _acting_person_id(request, request.data.get("person_id"))
        if person_id is None:
            raise ValidationError({"detail": "No person to checkout on behalf of."})
        reward_ids = request.data.get("reward_ids") or []
        reqs = _domain_guard(
            services.checkout_cart, request.user, person_id=person_id, reward_ids=reward_ids
        )
        return Response(
            MeridianRewardRequestSerializer(reqs, many=True).data,
            status=status.HTTP_201_CREATED,
        )


class RewardRequestListView(APIView):
    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        reqs = selectors.list_reward_requests(status=request.query_params.get("status") or None)
        return Response(MeridianRewardRequestSerializer(reqs, many=True).data)


class RewardRequestApproveView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, request_id: int) -> Response:
        req = selectors.get_reward_request(request_id)
        if req is None:
            raise NotFound()
        req = _domain_guard(services.approve_reward_request, request.user, req)
        return Response(MeridianRewardRequestSerializer(req).data)


class RewardRequestRejectView(APIView):
    permission_classes = [_Perm]
    permission_action = "approve"

    def post(self, request: Request, request_id: int) -> Response:
        req = selectors.get_reward_request(request_id)
        if req is None:
            raise NotFound()
        req = _domain_guard(
            services.reject_reward_request, request.user, req,
            reason=request.data.get("reason", ""),
        )
        return Response(MeridianRewardRequestSerializer(req).data)


# ---------------------------------------------------------------------------
# Kiosk
# ---------------------------------------------------------------------------

class KioskMeridianView(APIView):
    """Kid-facing task/reward cards (Node Spec 13). Kiosk-safe subset only."""

    permission_classes = [_Perm]

    def get(self, request: Request) -> Response:
        person = getattr(request.user, "person_profile", None)
        person_id = person.id if person else None

        my_tasks = selectors.list_tasks(request.user, assigned_to_person_id=person_id, active_only=True) \
            if person_id else selectors.list_tasks(request.user, active_only=True)
        # Only show actionable cards on the kiosk: available or pending mine.
        my_tasks = [t for t in my_tasks if t.status in ("available", "pending")]

        balance = services.get_points_balance(person_id) if person_id else 0
        rewards = selectors.list_rewards(active_only=True, hide_out_of_stock=True)

        return Response({
            "person_id": person_id,
            "points_balance": balance,
            "tasks": MeridianTaskSerializer(my_tasks, many=True).data,
            "rewards": MeridianRewardSerializer(rewards, many=True).data,
        })
