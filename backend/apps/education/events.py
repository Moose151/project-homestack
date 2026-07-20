"""education domain events published to the event bus (D4).

Publish-only in the uni-first V1 slice. Consumers (e.g. Meridian generating a rewarded
homework task from `homework_created`) are wired in a later slice per Node Spec 11.
"""
from apps.events.bus import publish


def assessment_created(assessment_id: int, household_id: int) -> None:
    publish("education.assessment_created", payload={
        "assessment_id": assessment_id, "household_id": household_id,
    })


def assessment_completed(assessment_id: int, household_id: int) -> None:
    publish("education.assessment_completed", payload={
        "assessment_id": assessment_id, "household_id": household_id,
    })


def class_session_created(session_id: int, household_id: int) -> None:
    publish("education.class_session_created", payload={
        "session_id": session_id, "household_id": household_id,
    })


def school_event_created(event_id: int, household_id: int) -> None:
    publish("education.school_event_created", payload={
        "event_id": event_id, "household_id": household_id,
    })
