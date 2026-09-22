"""The bounded set of source actions Hub may offer on an Upcoming row.

Hub deliberately does not implement cross-domain write logic (Core Hub spec §11). This
registry is the opposite of that: one explicit entry per record type whose owning domain
*already* has an unambiguous "this is finished" service, mapped to that service.

Every entry delegates to the owning node's service layer, so business rules, Calendar
sync (D7), events and notifications stay where they belong. Hub contributes only two
things: the permission check on the owning node, and the label the row shows.

Adding a record type here is a deliberate product decision, not a convenience. A domain
whose completion needs more than one input (which person did it, how much was paid)
belongs in its own screen and must stay out of this table.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class UpcomingAction:
    """One completion transition Hub may perform on behalf of an owning node."""

    label: str            # what the button says — the owning domain's own word
    resource: str         # node key the permission check runs against
    load: Callable        # (record_id) -> model instance or None
    complete: Callable    # (acting_user, record) -> None
    # The permission action the owning node's own completion view gates on. Meridian uses
    # `complete` rather than `edit` precisely so children can finish their own tasks; Hub
    # has to ask the same question the node asks, or the Dashboard would be stricter than
    # the screen it mirrors.
    action: str = "edit"
    # Optional (acting_user, record) -> bool. Some transitions need more than the record to
    # be well-defined; offering a button that is guaranteed to fail is worse than offering
    # none, so those actions answer for themselves rather than failing on tap.
    is_available: Callable | None = None


def _atlas_list_item():
    from apps.atlas.models import AtlasListItem
    from apps.atlas.services import complete_list_item

    return UpcomingAction(
        label="Done",
        resource="atlas",
        load=lambda pk: AtlasListItem.objects.filter(pk=pk).first(),
        complete=lambda user, item: complete_list_item(user, item),
    )


def _education_assessment():
    from apps.education.models import EducationAssessment
    from apps.education.services import update_assessment

    return UpcomingAction(
        label="Done",
        resource="education",
        load=lambda pk: EducationAssessment.objects.filter(pk=pk).first(),
        complete=lambda user, obj: update_assessment(
            user, obj, status=EducationAssessment.Status.DONE
        ),
    )


def _meridian_task():
    from apps.meridian.models import MeridianTask
    from apps.meridian.services import complete_task

    def _person_id_for(user, task):
        """Who the completion is recorded against — Meridian records work against a Person.

        Mirrors Meridian's own view: the Person linked to the acting user, falling back to
        the task's sole assignee. With neither, there is no unambiguous answer and the task
        has to be completed from Meridian itself, where the completer can be chosen.
        """
        person = getattr(user, "person_profile", None)
        if person is not None:
            return person.id
        assignees = list(task.assigned_to_people.values_list("id", flat=True))
        return assignees[0] if len(assignees) == 1 else None

    def _complete(user, task):
        complete_task(user, task, person_id=_person_id_for(user, task))

    return UpcomingAction(
        label="Done",
        resource="meridian",
        action="complete",
        load=lambda pk: MeridianTask.objects.filter(pk=pk).first(),
        complete=_complete,
        is_available=lambda user, task: _person_id_for(user, task) is not None,
    )


def _maintenance_task():
    from apps.homestead.models import MaintenanceTask
    from apps.homestead.services import complete_maintenance

    return UpcomingAction(
        label="Done",
        resource="homestead",
        load=lambda pk: MaintenanceTask.objects.filter(pk=pk).first(),
        complete=lambda user, obj: complete_maintenance(user, obj),
    )


def _pet_treatment():
    from apps.pets.models import PetTreatment
    from apps.pets.services import complete_treatment

    return UpcomingAction(
        label="Done",
        resource="pets",
        load=lambda pk: PetTreatment.objects.filter(pk=pk).first(),
        complete=lambda user, obj: complete_treatment(user, obj),
    )


def _bill():
    from apps.solace.models import Bill
    from apps.solace.services import mark_bill_paid

    return UpcomingAction(
        # Money's own word for "finished" is Paid, not Done. Sharing one interaction does
        # not mean flattening each domain's vocabulary.
        label="Paid",
        resource="solace",
        load=lambda pk: Bill.objects.filter(pk=pk).first(),
        complete=lambda user, obj: mark_bill_paid(user, obj),
    )


# Built lazily so importing Hub does not import six other node apps at startup.
_BUILDERS = {
    "AtlasListItem": _atlas_list_item,
    "Bill": _bill,
    "EducationAssessment": _education_assessment,
    "MaintenanceTask": _maintenance_task,
    "MeridianTask": _meridian_task,
    "PetTreatment": _pet_treatment,
}


def action_for(source_record_type: str) -> UpcomingAction | None:
    builder = _BUILDERS.get(source_record_type or "")
    return builder() if builder else None


def domain_errors() -> tuple[type[Exception], ...]:
    """Error types the registered services raise to refuse a transition.

    These mean "the domain declined", not "the server broke", so Hub answers 400 rather than
    letting them surface as a 500. Deliberately an explicit tuple: catching bare Exception
    here would quietly turn real bugs into polite error messages.
    """
    from apps.meridian.services import MeridianError

    return (MeridianError, ValueError)


def action_label(source_record_type: str, *, acting_user=None, record=None) -> str | None:
    """The label to advertise on an Upcoming row, or None when it has no usable action."""
    action = action_for(source_record_type)
    if action is None:
        return None
    if action.is_available is not None and acting_user is not None and record is not None:
        if not action.is_available(acting_user, record):
            return None
    return action.label
