from apps.homestead.models import RoomPlanItem, RoomPlanProduct
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility


def provide(*, user, person, since):
    rows = apply_visibility(
        RoomPlanItem.objects.filter(assigned_to_people=person).select_related("room").prefetch_related("products"), user
    )
    assignments = [{
        "key": f"homestead:room-item:{row.id}", "source_node": "homestead", "kind": "room_plan",
        "title": row.title, "summary": row.room.name, "due_at": None,
        "action_url": f"/homestead/rooms/{row.room_id}?plan_item={row.id}",
    } for row in rows.exclude(status__in=["completed", "archived"])]
    activity = [{
        "key": f"homestead:room-item:{row.id}:completed", "source_node": "homestead",
        "kind": "room_completion", "title": f"Completed {row.title}", "summary": row.room.name,
        "occurred_at": row.completed_at.isoformat(), "action_url": f"/homestead/rooms/{row.room_id}?plan_item={row.id}",
    } for row in rows.filter(status="completed", completed_at__gte=since)]
    if person.linked_user_id:
        activity.extend({
            "key": f"homestead:room-item:{row.id}:created", "source_node": "homestead",
            "kind": "room_plan_created", "title": f"Added {row.title} to a room plan",
            "summary": row.room.name, "occurred_at": row.created_at.isoformat(),
            "action_url": f"/homestead/rooms/{row.room_id}?plan_item={row.id}",
        } for row in rows.filter(created_by_id=person.linked_user_id, created_at__gte=since))
        visible_item_ids = rows.values_list("id", flat=True)
        products = RoomPlanProduct.objects.filter(
            plan_item_id__in=visible_item_ids, created_by_id=person.linked_user_id,
            created_at__gte=since,
        ).select_related("plan_item__room")
        activity.extend({
            "key": f"homestead:room-product:{row.id}:created", "source_node": "homestead",
            "kind": "room_product_added", "title": f"Added {row.title}",
            "summary": f"{row.plan_item.room.name} · {row.plan_item.title}",
            "occurred_at": row.created_at.isoformat(),
            "action_url": f"/homestead/rooms/{row.plan_item.room_id}?plan_item={row.plan_item_id}&product={row.id}",
        } for row in products)
    collections = [{
        "key": f"homestead:room-item:{row.id}:products", "source_node": "homestead",
        "kind": "room_plan", "title": row.title,
        "summary": f"{row.room.name} · {len(row.products.all())} options",
        "action_url": f"/homestead/rooms/{row.room_id}?plan_item={row.id}",
    } for row in rows if row.products.all()]
    return {"activity": activity, "assignments": assignments, "collections": collections}


register("homestead", provide)
