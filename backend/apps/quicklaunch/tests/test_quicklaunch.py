"""Quick Launch — a shortcut is a convenience, never a capability.

The governing rule these tests defend: a shortcut grants no access it did not already have. It
stores an intent, and every launch re-asks the ordinary questions — is this person the owner, is
the node enabled, do they hold the permission, does the record still exist, is the sensitive gate
satisfied. Anything that starts passing because a route was cached or a check was skipped is a
regression.
"""
from __future__ import annotations

import uuid

from django.test import TestCase
from django.urls import reverse
from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import get_active_household
from apps.quicklaunch import services
from apps.quicklaunch.models import QuickLaunchShortcut

SHORTCUTS = "/api/v1/quick-launch/shortcuts/"
TARGETS = "/api/v1/quick-launch/targets/"


def _user(username, role="admin", pin="1234"):
    user = User.objects.create_user(
        username=username, display_name=username.title(), role=role, password="test-pass-123",
    )
    user.set_pin(pin)
    user.save()
    return user


def _login(client, username, pin="1234"):
    client.post(
        reverse("auth-pin-login"), {"username": username, "pin": pin},
        content_type="application/json",
    )


def _resolve_url(shortcut):
    return f"{SHORTCUTS}{shortcut.public_id}/resolve/"


def _detail_url(shortcut):
    return f"{SHORTCUTS}{shortcut.public_id}/"


class ShortcutCrudTests(TestCase):
    def setUp(self):
        self.user = _user("ql-user")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_and_list(self):
        response = self.client.post(
            SHORTCUTS, {"target_key": "core.calendar"}, format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["label"], "Calendar")
        listing = self.client.get(SHORTCUTS)
        self.assertEqual(len(listing.data), 1)

    def test_the_public_id_is_a_uuid_not_the_row_id(self):
        response = self.client.post(SHORTCUTS, {"target_key": "core.calendar"}, format="json")
        uuid.UUID(str(response.data["id"]))          # parses
        shortcut = QuickLaunchShortcut.objects.get()
        self.assertNotEqual(str(response.data["id"]), str(shortcut.pk))

    def test_rename(self):
        created = self.client.post(SHORTCUTS, {"target_key": "core.calendar"}, format="json")
        shortcut = QuickLaunchShortcut.objects.get(public_id=created.data["id"])
        response = self.client.patch(
            _detail_url(shortcut), {"custom_label": "Family diary"}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["label"], "Family diary")

    def test_delete(self):
        created = self.client.post(SHORTCUTS, {"target_key": "core.calendar"}, format="json")
        shortcut = QuickLaunchShortcut.objects.get(public_id=created.data["id"])
        self.assertEqual(self.client.delete(_detail_url(shortcut)).status_code, 204)
        self.assertEqual(self.client.get(SHORTCUTS).data, [])

    def test_reorder(self):
        keys = ["core.calendar", "core.dashboard"]
        ids = [
            self.client.post(SHORTCUTS, {"target_key": key}, format="json").data["id"]
            for key in keys
        ]
        response = self.client.patch(
            f"{SHORTCUTS}reorder/", {"ids": [ids[1], ids[0]]}, format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["target_key"] for row in response.data],
                         ["core.dashboard", "core.calendar"])

    def test_the_same_destination_cannot_be_added_twice(self):
        self.client.post(SHORTCUTS, {"target_key": "core.calendar"}, format="json")
        second = self.client.post(SHORTCUTS, {"target_key": "core.calendar"}, format="json")
        self.assertEqual(second.status_code, 400)

    def test_a_cap_applies(self):
        from apps.quicklaunch.services import MAX_SHORTCUTS
        for index in range(MAX_SHORTCUTS):
            QuickLaunchShortcut.objects.create(
                household=get_active_household(), user=self.user,
                target_key="core.calendar", target_object_id=index,
                created_by=self.user, updated_by=self.user,
            )
        response = self.client.post(SHORTCUTS, {"target_key": "core.dashboard"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_anonymous_is_refused(self):
        client = APIClient()
        self.assertEqual(client.get(SHORTCUTS).status_code, 403)
        self.assertEqual(client.get(TARGETS).status_code, 403)


class TargetValidationTests(TestCase):
    """Nothing a client sends may become a route."""

    def setUp(self):
        self.user = _user("ql-validate")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_unknown_target_is_rejected(self):
        for key in ("nonsense", "core.does_not_exist", ""):
            self.assertEqual(
                self.client.post(SHORTCUTS, {"target_key": key}, format="json").status_code,
                400, key,
            )

    def test_a_route_or_url_cannot_be_smuggled_in_as_a_target(self):
        for key in (
            "/admin/", "https://evil.example.com/steal", "javascript:alert(1)",
            "../../etc/passwd", "//evil.example.com",
        ):
            response = self.client.post(SHORTCUTS, {"target_key": key}, format="json")
            self.assertEqual(response.status_code, 400, key)
        self.assertEqual(QuickLaunchShortcut.objects.count(), 0)

    def test_an_object_id_on_a_target_that_takes_none_is_rejected(self):
        response = self.client.post(
            SHORTCUTS, {"target_key": "core.calendar", "target_object_id": 1}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_an_object_backed_target_requires_an_object(self):
        response = self.client.post(SHORTCUTS, {"target_key": "atlas.list"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_a_nonexistent_object_is_rejected(self):
        response = self.client.post(
            SHORTCUTS, {"target_key": "atlas.list", "target_object_id": 999999}, format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_the_custom_label_is_bounded(self):
        created = self.client.post(
            SHORTCUTS, {"target_key": "core.calendar", "custom_label": "x" * 500}, format="json",
        )
        # Rejected by the serializer's max_length rather than silently truncated.
        self.assertEqual(created.status_code, 400)


class CrossUserIsolationTests(TestCase):
    """The regression the brief calls for: another person's identifier must be useless."""

    def setUp(self):
        self.alice = _user("ql-alice")
        self.bob = _user("ql-bob")
        self.alice_shortcut = services.create_shortcut(self.alice, target_key="core.calendar")
        self.client = APIClient()
        self.client.force_authenticate(self.bob)

    def test_bob_does_not_see_alices_shortcut(self):
        self.assertEqual(self.client.get(SHORTCUTS).data, [])

    def test_bob_cannot_resolve_alices_shortcut_by_changing_the_identifier(self):
        response = self.client.get(_resolve_url(self.alice_shortcut))
        self.assertEqual(response.status_code, 404)
        # And the answer discloses nothing about where it would have gone.
        self.assertNotIn("route", response.data)

    def test_bob_cannot_rename_alices_shortcut(self):
        response = self.client.patch(
            _detail_url(self.alice_shortcut), {"custom_label": "Mine now"}, format="json",
        )
        self.assertEqual(response.status_code, 404)
        self.alice_shortcut.refresh_from_db()
        self.assertEqual(self.alice_shortcut.custom_label, "")

    def test_bob_cannot_delete_alices_shortcut(self):
        self.assertEqual(self.client.delete(_detail_url(self.alice_shortcut)).status_code, 404)
        self.assertTrue(QuickLaunchShortcut.objects.filter(pk=self.alice_shortcut.pk).exists())

    def test_bob_cannot_reorder_alices_shortcut_into_his_own_list(self):
        self.client.patch(
            f"{SHORTCUTS}reorder/", {"ids": [str(self.alice_shortcut.public_id)]}, format="json",
        )
        self.alice_shortcut.refresh_from_db()
        self.assertEqual(self.alice_shortcut.user_id, self.alice.id)
        self.assertEqual(self.client.get(SHORTCUTS).data, [])

    def test_an_unknown_identifier_answers_the_same_way_as_someone_elses(self):
        """Otherwise the difference itself confirms a shortcut exists."""
        theirs = self.client.get(_resolve_url(self.alice_shortcut))
        nothing = self.client.get(f"{SHORTCUTS}{uuid.uuid4()}/resolve/")
        self.assertEqual(theirs.status_code, nothing.status_code)
        self.assertEqual(theirs.data["reason"], nothing.data["reason"])


class ResolutionTests(TestCase):
    def setUp(self):
        self.user = _user("ql-resolve")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_an_ordinary_destination_resolves_to_its_route(self):
        shortcut = services.create_shortcut(self.user, target_key="core.calendar")
        response = self.client.get(_resolve_url(shortcut))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ok")
        self.assertEqual(response.data["route"], "/calendar")

    def test_a_disabled_node_makes_its_shortcut_unavailable(self):
        from apps.nodes.services import disable_node, enable_node

        enable_node(self.user, "atlas")
        shortcut = services.create_shortcut(self.user, target_key="atlas.todos")
        self.assertEqual(self.client.get(_resolve_url(shortcut)).data["status"], "ok")

        disable_node(self.user, "atlas")
        response = self.client.get(_resolve_url(shortcut))
        self.assertEqual(response.data["status"], "unavailable")
        self.assertNotIn("route", response.data)
        self.assertIn("no longer available", response.data["reason"])

    def test_a_deleted_record_makes_its_shortcut_unavailable(self):
        from apps.atlas.services import create_atlas_list, delete_atlas_list
        from apps.nodes.services import enable_node

        enable_node(self.user, "atlas")
        atlas_list = create_atlas_list(self.user, title="Packing", list_type="checklist")
        shortcut = services.create_shortcut(
            self.user, target_key="atlas.list", target_object_id=atlas_list.id,
        )
        self.assertEqual(self.client.get(_resolve_url(shortcut)).data["status"], "ok")

        delete_atlas_list(self.user, atlas_list)
        response = self.client.get(_resolve_url(shortcut))
        self.assertEqual(response.data["status"], "unavailable")
        # The deleted record's name must not leak through the failure.
        self.assertNotIn("Packing", str(response.data))

    def test_a_target_removed_from_the_registry_fails_gracefully(self):
        shortcut = services.create_shortcut(self.user, target_key="core.calendar")
        QuickLaunchShortcut.objects.filter(pk=shortcut.pk).update(target_key="retired.target")
        shortcut.refresh_from_db()
        response = self.client.get(_resolve_url(shortcut))
        self.assertEqual(response.data["status"], "unavailable")

    def test_a_specific_list_resolves_to_its_own_deep_link(self):
        from apps.atlas.services import create_atlas_list
        from apps.nodes.services import enable_node

        enable_node(self.user, "atlas")
        atlas_list = create_atlas_list(self.user, title="Packing", list_type="checklist")
        shortcut = services.create_shortcut(
            self.user, target_key="atlas.list", target_object_id=atlas_list.id,
        )
        route = self.client.get(_resolve_url(shortcut)).data["route"]
        self.assertEqual(route, f"/atlas?tab=lists&list={atlas_list.id}")

    def test_the_label_falls_back_to_the_record_name(self):
        from apps.atlas.services import create_atlas_list
        from apps.nodes.services import enable_node

        enable_node(self.user, "atlas")
        atlas_list = create_atlas_list(self.user, title="Packing", list_type="checklist")
        shortcut = services.create_shortcut(
            self.user, target_key="atlas.list", target_object_id=atlas_list.id,
        )
        self.assertEqual(self.client.get(_resolve_url(shortcut)).data["label"], "Packing")


class SensitiveTargetTests(TestCase):
    """Money behaves through a shortcut exactly as it does through ordinary navigation."""

    def setUp(self):
        self.user = _user("ql-money")
        from apps.nodes.services import enable_node
        enable_node(self.user, "solace")
        from apps.permissions.services import grant_user_permission
        grant_user_permission(self.user, "solace.view")
        self.shortcut = services.create_shortcut(self.user, target_key="solace.upcoming_bills")
        # A session client, not force_authenticate: re-authentication lives in the session, so
        # the test has to exercise the same login the app uses.
        self.client = Client()

    def _set_lock(self, required):
        from apps.nodes.models import HouseholdNode
        HouseholdNode.objects.filter(node__key="solace").update(
            requires_reauthentication=required,
        )

    def test_a_locked_money_shortcut_reports_locked_not_open(self):
        self._set_lock(True)
        _login(self.client, "ql-money")
        response = self.client.get(_resolve_url(self.shortcut))
        self.assertEqual(response.data["status"], "locked")
        self.assertIn("Unlock", response.data["reason"])

    def test_the_intended_destination_survives_the_unlock(self):
        """The client sends the user through re-auth and returns here; the route is preserved."""
        self._set_lock(True)
        _login(self.client, "ql-money")
        locked = self.client.get(_resolve_url(self.shortcut))
        self.assertEqual(locked.data["route"], "/solace?tab=bills&section=upcoming")

        reauthed = self.client.post(
            reverse("auth-reauth"), {"password": "test-pass-123"},
            content_type="application/json",
        )
        self.assertEqual(reauthed.status_code, 200, reauthed.data)
        unlocked = self.client.get(_resolve_url(self.shortcut))
        self.assertEqual(unlocked.data["status"], "ok")
        self.assertEqual(unlocked.data["route"], locked.data["route"])

    def test_money_opens_directly_when_the_household_lock_is_off(self):
        self._set_lock(False)
        _login(self.client, "ql-money")
        self.assertEqual(self.client.get(_resolve_url(self.shortcut)).data["status"], "ok")

    def test_losing_the_permission_makes_the_shortcut_unavailable(self):
        from apps.permissions.services import deny_user_permission

        self._set_lock(False)
        deny_user_permission(self.user, "solace.view")
        _login(self.client, "ql-money")
        response = self.client.get(_resolve_url(self.shortcut))
        self.assertEqual(response.data["status"], "unavailable")
        self.assertNotIn("route", response.data)


class CatalogueTests(TestCase):
    def setUp(self):
        self.user = _user("ql-catalogue")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _keys(self):
        return {row["key"] for row in self.client.get(TARGETS).data["targets"]}

    def test_core_targets_are_always_offered(self):
        keys = self._keys()
        self.assertIn("core.dashboard", keys)
        self.assertIn("core.calendar", keys)

    def test_a_disabled_node_is_not_offered(self):
        from apps.nodes.services import disable_node, enable_node

        enable_node(self.user, "atlas")
        self.assertIn("atlas.home", self._keys())
        disable_node(self.user, "atlas")
        self.assertNotIn("atlas.home", self._keys())

    def test_an_object_target_with_nothing_to_point_at_is_not_offered(self):
        from apps.nodes.services import enable_node

        enable_node(self.user, "atlas")
        # Grocery and the Household To-do list always exist (atlas.0010) and have their own
        # object-free targets, so "a list" means a Lists & Notes list — and there are none yet.
        self.assertNotIn("atlas.list", self._keys())

        from apps.atlas.services import create_atlas_list
        create_atlas_list(self.user, title="Packing", list_type="checklist")
        self.assertIn("atlas.list", self._keys())

    def test_the_catalogue_never_exposes_internal_node_names_as_labels(self):
        from apps.nodes.services import enable_node

        for node in ("atlas", "meridian", "solace", "homestead"):
            enable_node(self.user, node)
        from apps.permissions.services import grant_user_permission
        grant_user_permission(self.user, "solace.view")

        for row in self.client.get(TARGETS).data["targets"]:
            for internal in ("Atlas", "Meridian", "Solace", "Homestead"):
                self.assertNotIn(internal, row["label"], row["key"])
                self.assertNotIn(internal, row["description"], row["key"])

    def test_an_action_target_is_advertised_as_such(self):
        from apps.nodes.services import enable_node
        enable_node(self.user, "fitness")
        rows = {row["key"]: row for row in self.client.get(TARGETS).data["targets"]}
        self.assertEqual(rows["fitness.log_run"]["target_type"], "action")


class ActionTargetTests(TestCase):
    """An action shortcut opens a form. It never performs the action by itself."""

    def setUp(self):
        self.user = _user("ql-action")
        from apps.nodes.services import enable_node
        enable_node(self.user, "fitness")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_resolving_log_run_opens_the_form_and_creates_nothing(self):
        from apps.fitness.models import WorkoutSession

        shortcut = services.create_shortcut(self.user, target_key="fitness.log_run")
        response = self.client.get(_resolve_url(shortcut))
        self.assertEqual(response.data["status"], "ok")
        self.assertIn("new=run", response.data["route"])
        # Merely opening the shortcut must not log a run.
        self.assertEqual(WorkoutSession.objects.count(), 0)


class AtlasDestinationTests(TestCase):
    """Quick Launch was built against the pre-v0.40 Atlas.

    A shortcut stores intent and resolves a route at launch time, which is exactly what makes a
    stale registry entry silent: "Reminders" kept resolving to `/atlas?tab=reminders` long after
    that tab stopped existing, and the user would just land on the default tab with no error.
    These pin the destinations to the tabs Atlas actually has.
    """

    def setUp(self):
        self.user = _user("ql-atlas")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        from apps.nodes.services import enable_node
        enable_node(self.user, "atlas")

    def _keys(self):
        return {row["key"] for row in self.client.get(TARGETS).data["targets"]}

    def _route(self, **kwargs):
        shortcut = services.create_shortcut(self.user, **kwargs)
        return self.client.get(_resolve_url(shortcut)).data

    def test_the_retired_reminders_destination_is_gone(self):
        self.assertNotIn("atlas.reminders", self._keys())

    def test_grocery_and_todos_are_offered_as_their_own_destinations(self):
        keys = self._keys()
        self.assertIn("atlas.grocery", keys)
        self.assertIn("atlas.todos", keys)

    def test_grocery_and_todos_resolve_to_real_tabs(self):
        self.assertEqual(self._route(target_key="atlas.grocery")["route"], "/atlas?tab=grocery")
        self.assertEqual(self._route(target_key="atlas.todos")["route"], "/atlas?tab=todos")

    def test_a_grocery_list_is_not_offered_as_a_generic_list_choice(self):
        """Grocery is one household list with its own entry — offering it twice, once as "a
        list", would put the same destination in the picker under two different names."""
        from apps.atlas.services import ensure_household_grocery_list

        grocery = ensure_household_grocery_list(self.user)
        targets = {row["key"]: row for row in self.client.get(TARGETS).data["targets"]}
        offered = {obj["id"] for obj in targets.get("atlas.list", {}).get("objects", [])}
        self.assertNotIn(grocery.id, offered)

    def test_a_personal_todo_list_resolves_to_the_todos_tab(self):
        from apps.atlas.services import ensure_household_todo_list

        todo_list = ensure_household_todo_list(self.user)
        resolved = self._route(target_key="atlas.todo_list", target_object_id=todo_list.id)
        self.assertEqual(resolved["route"], f"/atlas?tab=todos&list={todo_list.id}")

    def test_a_lists_and_notes_list_resolves_to_the_lists_tab(self):
        from apps.atlas.services import create_atlas_list

        checklist = create_atlas_list(self.user, title="Packing", list_type="checklist")
        resolved = self._route(target_key="atlas.list", target_object_id=checklist.id)
        self.assertEqual(resolved["route"], f"/atlas?tab=lists&list={checklist.id}")

    def test_no_atlas_destination_points_at_a_tab_the_page_does_not_have(self):
        """A guard against the next rename, not just this one."""
        from apps.quicklaunch.registry import REGISTRY

        real_tabs = {"grocery", "todos", "lists", "agenda", "schedule", "people"}
        from apps.atlas.services import create_atlas_list, ensure_household_todo_list
        objects = {
            "atlas.list": create_atlas_list(self.user, title="Packing", list_type="checklist"),
            "atlas.todo_list": ensure_household_todo_list(self.user),
        }
        for key, target in REGISTRY.items():
            if not key.startswith("atlas."):
                continue
            route = target.route(self.user, objects.get(key))
            if "tab=" not in route:
                continue
            tab = route.split("tab=")[1].split("&")[0]
            self.assertIn(tab, real_tabs, f"{key} points at a tab Atlas does not have")

    def test_a_shortcut_into_atlas_still_dies_with_the_node(self):
        from apps.nodes.services import disable_node

        shortcut = services.create_shortcut(self.user, target_key="atlas.todos")
        disable_node(self.user, "atlas")
        self.assertEqual(
            self.client.get(_resolve_url(shortcut)).data["status"], "unavailable",
        )
