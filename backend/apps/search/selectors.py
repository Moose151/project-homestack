"""Permission-aware aggregation for HomeStack global search."""
from __future__ import annotations

from urllib.parse import quote

from apps.accounts.services import is_reauthed
from apps.nodes.models import HouseholdNode
from apps.permissions.selectors import list_permissions_for_user


def _result(node: str, kind: str, obj, title: str, subtitle: str, route: str) -> dict:
    return {
        "node": node,
        "kind": kind,
        "id": obj.pk,
        "title": title,
        "subtitle": subtitle,
        "route": route,
    }


def search_all(request, query: str, *, per_node_limit: int = 8) -> dict:
    """Search enabled, permitted surfaces and return a small normalized result set."""
    user = request.user
    encoded = quote(query)
    enabled = set(
        HouseholdNode.objects.filter(
            household=user.household,
            is_enabled=True,
            is_hidden=False,
        ).values_list("node__key", flat=True)
    )
    unlocked = is_reauthed(request)
    permissions = set(list_permissions_for_user(user))
    results: list[dict] = []
    locked_nodes: list[str] = []

    def allowed(node: str, resource: str | None = None) -> bool:
        return node in enabled and f"{resource or node}.view" in permissions

    def add_node(rows: list[dict]) -> None:
        results.extend(rows[:per_node_limit])

    if "scheduling.view" in permissions:
        from apps.scheduling.selectors import search_events
        events = search_events(user, query, sensitive_unlocked=unlocked)
        add_node([
            _result(
                "calendar", "event", event, event.title,
                event.location or ("All day" if event.is_all_day else event.start_at.isoformat()),
                f"/calendar?date={event.start_at.date().isoformat()}",
            )
            for event in events
        ])

    if allowed("atlas"):
        from apps.atlas import selectors
        found = selectors.search_atlas(user, query)
        add_node([
            *[_result("atlas", "list", row, row.title, "List", f"/atlas?tab=lists&q={encoded}") for row in found["lists"]],
            *[_result("atlas", "item", row, row.title, "List item", f"/atlas?tab=lists&q={encoded}") for row in found["items"]],
            *[_result("atlas", "note", row, row.title, "Note", f"/atlas?tab=notes&q={encoded}") for row in found["notes"]],
            *[_result("atlas", "reminder", row, row.title, "Reminder", f"/atlas?tab=reminders&q={encoded}") for row in found["reminders"]],
        ])

    if allowed("meridian"):
        from apps.meridian import selectors
        found = selectors.search_meridian(user, query)
        add_node([
            *[_result("meridian", "task", row, row.title, "Task", f"/meridian?tab=tasks&q={encoded}") for row in found["tasks"]],
            *[_result("meridian", "reward", row, row.name, "Reward", f"/meridian?tab=shop&q={encoded}") for row in found["rewards"]],
            *[_result("meridian", "category", row, row.name, "Category", "/meridian?tab=settings") for row in found["categories"]],
        ])

    if allowed("education"):
        from apps.education import selectors
        found = selectors.search_education(user, query)
        add_node([
            *[_result("education", "course", row, row.name, row.code or "Course", f"/education?tab=courses&q={encoded}") for row in found["courses"]],
            *[_result("education", "assessment", row, row.title, "Assignment", f"/education?tab=assignments&q={encoded}") for row in found["assessments"]],
            *[_result("education", "class", row, row.display_title, "Class", f"/education?tab=timetable&q={encoded}") for row in found["class_sessions"]],
            *[_result("education", "event", row, row.title, "Education event", f"/education?tab=events&q={encoded}") for row in found["events"]],
        ])

    if allowed("books"):
        from apps.books import selectors
        add_node([
            _result("books", "book", row, row.title, row.author or "Book", f"/books?q={encoded}")
            for row in selectors.list_books(query)
        ])

    if allowed("home_wiki"):
        from apps.home_wiki import selectors
        add_node([
            _result("home_wiki", "page", row, row.title, row.category.name if row.category else "Wiki page", f"/wiki?q={encoded}")
            for row in selectors.search_wiki(user, query)
        ])

    if allowed("pets"):
        from apps.pets import selectors
        found = selectors.search_pets(user, query)
        add_node([
            *[_result("pets", "pet", row, row.name, "Pet", f"/pets?tab=pets&q={encoded}") for row in found["pets"]],
            *[_result("pets", "treatment", row, row.display_name, row.pet.name, f"/pets?tab=reminders&q={encoded}") for row in found["treatments"]],
            *[_result("pets", "appointment", row, row.display_title, row.pet.name, f"/pets?tab=appointments&q={encoded}") for row in found["appointments"]],
        ])

    if allowed("homestead"):
        from apps.homestead import selectors
        found = selectors.search_homestead(user, query)
        add_node([
            *[_result("homestead", "maintenance", row, row.title, "Maintenance", f"/homestead?tab=maintenance&q={encoded}") for row in found["maintenance"]],
            *[_result("homestead", "appliance", row, row.name, row.room or "Appliance", f"/homestead?tab=appliances&q={encoded}") for row in found["appliances"]],
            *[_result("homestead", "improvement", row, row.title, "Improvement", f"/homestead?tab=improvements&q={encoded}") for row in found["improvements"]],
            *[_result("homestead", "provider", row, row.name, row.company or "Contact", f"/homestead?tab=contacts&q={encoded}") for row in found["providers"]],
            *[_result("homestead", "room", row, row.name, "Room / area", f"/homestead/rooms/{row.id}") for row in found["rooms"]],
            *[_result("homestead", "room_item", row, row.title, row.room.name, f"/homestead/rooms/{row.room_id}") for row in found["room_items"]],
        ])

    if allowed("solace"):
        if not unlocked:
            locked_nodes.append("solace")
        else:
            from apps.audit.helpers import log_audit
            from apps.nodes.models import Node
            from apps.solace import selectors
            found = selectors.search_solace(user, query)
            log_audit(
                "sensitive_node_accessed",
                user=user,
                target_node=Node.objects.filter(key="solace").first(),
                request=request,
                metadata={"node": "solace", "path": request.path, "method": request.method},
            )
            add_node([
                *[_result("solace", "bill", row, row.name, "Bill", f"/solace?tab=bills&q={encoded}") for row in found["bills"]],
                *[_result("solace", "payday", row, row.title, "Payday", f"/solace?tab=paydays&q={encoded}") for row in found["paydays"]],
                *[_result("solace", "purchase", row, row.name, "Purchase", f"/solace?tab=purchases&q={encoded}") for row in found["purchases"]],
                *[_result("solace", "bucket", row, row.name, "Bucket", f"/solace?tab=buckets&q={encoded}") for row in found["buckets"]],
                *[_result("solace", "subscription", row, row.name, "Subscription", f"/solace?tab=subscriptions&q={encoded}") for row in found["subscriptions"]],
                *[_result("solace", "checklist", row, row.title, "Checklist", f"/solace?tab=checklist&q={encoded}") for row in found["checklist"]],
            ])

    return {"results": results, "locked_nodes": locked_nodes}
