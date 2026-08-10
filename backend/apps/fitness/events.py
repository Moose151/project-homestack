from apps.events.bus import publish


def session_completed(session_id: int, household_id: int, person_id: int, record_count: int) -> None:
    publish("fitness.session_completed", payload={
        "session_id": session_id, "household_id": household_id,
        "person_id": person_id, "record_count": record_count,
    })


def personal_record_set(record_id: int, household_id: int, person_id: int) -> None:
    publish("fitness.personal_record_set", payload={
        "record_id": record_id, "household_id": household_id, "person_id": person_id,
    })

