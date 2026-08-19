"""The destinations Quick Launch actually offers in this release.

Each entry names an existing, stable route contract — nothing here invents a destination or a
query parameter that the page does not already honour. Object-backed entries fetch their record
through the owning node's own selectors, so household scoping and visibility stay the node's
rules rather than a second copy of them that could drift.

Labels are the user-facing product names (Lists & Notes, Tasks, Money, Home). Internal node
keys (atlas, meridian, solace, homestead) appear only as `node_key`, which the client uses for
grouping and colour, never as display text.
"""
from __future__ import annotations

from apps.quicklaunch.registry import Target, register

# --- core surfaces --------------------------------------------------------------------------

register(Target(
    key="core.dashboard",
    label="Dashboard",
    description="Your household at a glance",
    icon="🏡",
    node_key="",
    target_type="open",
    route=lambda user, obj=None: "/hub",
))

register(Target(
    key="core.calendar",
    label="Calendar",
    description="Events, appointments and what is coming up",
    icon="📅",
    node_key="",
    target_type="open",
    route=lambda user, obj=None: "/calendar",
))

# --- Lists & Notes --------------------------------------------------------------------------

register(Target(
    key="atlas.home",
    label="Lists & Notes",
    description="Everything in Lists & Notes",
    icon="🗒",
    node_key="atlas",
    target_type="open",
    route=lambda user, obj=None: "/atlas",
))

register(Target(
    key="atlas.grocery",
    label="Grocery",
    description="The household grocery list",
    icon="🛒",
    node_key="atlas",
    target_type="open",
    route=lambda user, obj=None: "/atlas?tab=grocery",
))

register(Target(
    key="atlas.todos",
    label="To-dos",
    description="Household and personal to-dos",
    icon="✅",
    node_key="atlas",
    target_type="open",
    route=lambda user, obj=None: "/atlas?tab=todos",
))


# Atlas has exactly three list tabs since v0.40 (D19): Grocery, To-dos, Lists & Notes. The old
# standalone "Reminders" destination is gone with the object it pointed at — a reminder is now a
# property of a To-do, so "/atlas?tab=reminders" leads nowhere. Grocery and To-dos are single,
# always-present destinations and get their own entries above; the object-backed entries below
# cover the two kinds of list a household actually accumulates more than one of.

def _lists_and_notes_lists(user):
    """Selectable Lists & Notes lists — everything that is not Grocery or a To-do list.

    Legacy ``shopping``/``wishlist`` rows were folded into ``checklist`` by atlas.0010, but both
    types remain readable, so this matches on what a list is *not* rather than assuming they are
    all gone.
    """
    from apps.atlas import selectors
    return [
        (row.id, row.title)
        for row in selectors.list_atlas_lists(user)
        if row.list_type not in ("grocery", "todo")
    ]


def _todo_lists(user):
    """The Household To-do list plus each active person's. The node's own selector decides which
    of those this user may see, and drops lists belonging to deleted people."""
    from apps.atlas import selectors
    return [(row.id, row.title) for row in selectors.list_todo_lists(user)]


def _get_list(user, object_id):
    from apps.atlas import selectors
    return selectors.get_atlas_list(object_id, user)


def _list_tab(list_type: str) -> str:
    """Mirrors AtlasPage's own listTabFor()."""
    if list_type == "grocery":
        return "grocery"
    if list_type == "todo":
        return "todos"
    return "lists"


register(Target(
    key="atlas.list",
    label="A list",
    description="Open one particular list",
    icon="📋",
    node_key="atlas",
    target_type="open",
    requires_object=True,
    route=lambda user, obj: f"/atlas?tab={_list_tab(obj.list_type)}&list={obj.id}",
    list_objects=_lists_and_notes_lists,
    get_object=_get_list,
))

register(Target(
    key="atlas.todo_list",
    label="One to-do list",
    description="Open the Household list or one person's",
    icon="🗂",
    node_key="atlas",
    target_type="open",
    requires_object=True,
    route=lambda user, obj: f"/atlas?tab={_list_tab(obj.list_type)}&list={obj.id}",
    list_objects=_todo_lists,
    get_object=_get_list,
))

# --- Tasks ----------------------------------------------------------------------------------

register(Target(
    key="meridian.home",
    label="Tasks",
    description="Family jobs, points and goals",
    icon="⭐",
    node_key="meridian",
    target_type="open",
    route=lambda user, obj=None: "/meridian",
))

register(Target(
    key="meridian.tasks",
    label="Task list",
    description="The full task list",
    icon="✔",
    node_key="meridian",
    target_type="open",
    route=lambda user, obj=None: "/meridian?tab=tasks",
))

# --- Money ----------------------------------------------------------------------------------
# Sensitive: these resolve to a locked state until the household's re-authentication prompt has
# been satisfied, exactly as ordinary navigation into Money does.

register(Target(
    key="solace.home",
    label="Money",
    description="Bills, pay cycles and plans",
    icon="💸",
    node_key="solace",
    target_type="open",
    sensitive=True,
    route=lambda user, obj=None: "/solace",
))

register(Target(
    key="solace.upcoming_bills",
    label="Upcoming bills",
    description="Every unpaid bill in date order",
    icon="🧾",
    node_key="solace",
    target_type="open",
    sensitive=True,
    route=lambda user, obj=None: "/solace?tab=bills&section=upcoming",
))

# --- Home -----------------------------------------------------------------------------------

def _visible_rooms(user):
    from apps.homestead import selectors
    return [(row.id, row.name) for row in selectors.list_rooms(user)]


def _get_room(user, object_id):
    from apps.homestead import selectors
    return selectors.get_room(object_id, user)


register(Target(
    key="homestead.home",
    label="Home",
    description="Rooms, upkeep and services",
    icon="🏠",
    node_key="homestead",
    target_type="open",
    route=lambda user, obj=None: "/homestead",
))

register(Target(
    key="homestead.room",
    label="A room",
    description="Open one particular room",
    icon="🛋",
    node_key="homestead",
    target_type="open",
    requires_object=True,
    route=lambda user, obj: f"/homestead/rooms/{obj.id}",
    list_objects=lambda user: _visible_rooms(user),
    get_object=lambda user, object_id: _get_room(user, object_id),
))

# --- Fitness ----------------------------------------------------------------------------------
# An "action" target: it opens the Log run form ready to fill in. It never logs anything by
# itself — the user still presses Save (docs/39 §13).

register(Target(
    key="fitness.log_run",
    label="Log run",
    description="Open the quick run form",
    icon="🏃",
    node_key="fitness",
    target_type="action",
    route=lambda user, obj=None: "/fitness?tab=today&new=run",
))
