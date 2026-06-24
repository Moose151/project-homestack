"""
audit helpers — log_audit() is the single entry point for creating audit records.

Import this function anywhere; never instantiate AuditLog directly in other modules.
"""
from __future__ import annotations

from typing import Any


def _get_client_ip(request) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(
    action: str,
    *,
    household=None,
    user=None,
    target_node=None,
    target_record_type: str = "",
    target_record_id: int | None = None,
    request=None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Create an immutable AuditLog entry.

    action             — verb string, e.g. 'login', 'node_enabled', 'backup_restored'
    household          — defaults to the active household if None
    user               — the acting User; None for system-generated events
    target_node        — nodes.Node instance if the action targets a node
    target_record_type — dotted model name, e.g. 'accounts.User'
    target_record_id   — PK of the targeted record
    request            — HttpRequest for extracting IP + user-agent
    metadata           — arbitrary JSON-serialisable dict for extra context
    """
    from apps.audit.models import AuditLog
    from apps.core.models import get_active_household

    if household is None:
        household = get_active_household()
    if household is None:
        return  # DB not yet seeded (import scripts, empty test setups)

    ip_address: str | None = None
    user_agent: str = ""
    if request is not None:
        ip_address = _get_client_ip(request)
        user_agent = request.META.get("HTTP_USER_AGENT", "")

    AuditLog.objects.create(
        household=household,
        user=user,
        action=action,
        target_node=target_node,
        target_record_type=target_record_type,
        target_record_id=target_record_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
