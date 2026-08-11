from apps.atlas.models import AtlasList, AtlasListItem
from apps.atlas.serializers import AtlasListItemSerializer, AtlasListSuggestionSerializer
from apps.people.corner_registry import register
from apps.permissions.visibility import apply_visibility


def provide(*, user, person, since):
    visible_lists = apply_visibility(AtlasList.objects.all(), user)
    visible_ids = visible_lists.values_list("id", flat=True)
    assignments = [
        {"key": f"atlas:item:{row.id}", "source_node": "atlas", "kind": "list_item",
         "title": row.title, "summary": row.atlas_list.title,
         "due_at": row.due_at.isoformat() if row.due_at else None,
         "action_url": f"/atlas?tab=lists&list={row.atlas_list_id}"}
        for row in AtlasListItem.objects.filter(
            atlas_list_id__in=visible_ids, assigned_to_people=person, completed_at__isnull=True
        ).select_related("atlas_list")
    ]
    activity = []
    if person.linked_user_id:
        created = AtlasListItem.objects.filter(
            atlas_list_id__in=visible_ids, created_by_id=person.linked_user_id, created_at__gte=since
        ).select_related("atlas_list")
        activity.extend({
            "key": f"atlas:item:{row.id}:created", "source_node": "atlas", "kind": "created",
            "title": f"Added {row.title}", "summary": row.atlas_list.title,
            "occurred_at": row.created_at.isoformat(),
            "action_url": f"/atlas?tab=lists&list={row.atlas_list_id}",
        } for row in created)
        completed = AtlasListItem.objects.filter(
            atlas_list_id__in=visible_ids, completed_by_id=person.linked_user_id,
            completed_at__gte=since,
        ).select_related("atlas_list")
        activity.extend({
            "key": f"atlas:item:{row.id}:completed", "source_node": "atlas", "kind": "completed",
            "title": f"Completed {row.title}", "summary": row.atlas_list.title,
            "occurred_at": row.completed_at.isoformat(),
            "action_url": f"/atlas?tab=lists&list={row.atlas_list_id}",
        } for row in completed)
    collections = []
    for row in visible_lists.filter(owner_person=person).prefetch_related("items"):
        active_items = [item for item in row.items.all() if item.completed_at is None]
        collections.append({
            "key": f"atlas:list:{row.id}", "source_node": "atlas", "kind": row.list_type,
            "title": row.title, "summary": f"{len(active_items)} active items",
            "action_url": f"/atlas?tab=lists&list={row.id}", "list_id": row.id,
            "visibility": row.visibility, "items": AtlasListItemSerializer(active_items, many=True).data,
            "suggestions": AtlasListSuggestionSerializer(
                row.suggestions.filter(status="pending"), many=True,
            ).data if user.role in {"admin", "manager"} or row.owner_person.linked_user_id == user.id else [],
        })
    return {"activity": activity, "assignments": assignments, "collections": collections}


register("atlas", provide)
