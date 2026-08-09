"""One gate for every sensitive node (D10, Security §7).

Solace and Homestead each grew their own copy of "is this node locked, is the reader
re-authenticated, record that they looked". The copies had already drifted: Solace honoured the
household's `requires_reauthentication` setting so an admin could turn the extra prompt off,
while Homestead's finance surface ignored it and always prompted. A second node adding a third
copy is how a gap gets in.

`sensitive_node_access` builds the mixin for a node key. The lock decision comes from the
household's node configuration, falling back to the catalogue's `supports_sensitive_lock`, so
whether a node is sensitive is data rather than a hard-coded list of view classes.
"""
from __future__ import annotations

from rest_framework.exceptions import PermissionDenied
from rest_framework.request import Request

from apps.accounts.services import is_reauthed
from apps.audit.helpers import log_audit


def node_requires_reauth(node_key: str) -> bool:
    """Whether this household must re-enter a password to open the node.

    The household's own setting wins; a node with no configuration row falls back to whether
    the catalogue says it supports a sensitive lock at all. Unknown nodes are treated as locked
    rather than open — a missing row must not be a way past the gate.
    """
    from apps.nodes.models import Node
    from apps.nodes.selectors import get_household_node

    config = get_household_node(node_key)
    if config is not None:
        return config.requires_reauthentication

    node = Node.objects.filter(key=node_key).first()
    return node.supports_sensitive_lock if node is not None else True


def sensitive_node_access(node_key: str, *, surface: str = ""):
    """Build the access mixin for one sensitive node.

    Every request that gets through is audited, including read-only ones: the point of the
    record is who looked at the household's finances and when, not only who changed them.
    """

    class _SensitiveNodeAccessMixin:
        sensitive_node_key = node_key
        sensitive_surface = surface

        def initial(self, request: Request, *args, **kwargs) -> None:
            super().initial(request, *args, **kwargs)
            from apps.nodes.models import Node

            if node_requires_reauth(self.sensitive_node_key) and not is_reauthed(request._request):
                raise PermissionDenied(
                    "Password re-authentication required for this area."
                )
            log_audit(
                "sensitive_node_accessed",
                user=request.user,
                target_node=Node.objects.filter(key=self.sensitive_node_key).first(),
                request=request._request,
                metadata={
                    "node": self.sensitive_node_key,
                    "surface": self.sensitive_surface or self.sensitive_node_key,
                    "path": request.path,
                    "method": request.method,
                },
            )

    return _SensitiveNodeAccessMixin
