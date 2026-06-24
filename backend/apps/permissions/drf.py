"""
HomeStack DRF permission class (D10).

Wraps the central resolver into DRF's permission system so every view delegates to
one place. Views declare which resource they protect; the class maps HTTP methods to
resolver actions.

Usage in a view:
    from apps.permissions.drf import HomeStackPermission

    class PersonListView(APIView):
        permission_classes = [HomeStackPermission.for_resource("people")]
        ...

No view should check permissions any other way (D10).
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.permissions.resolver import resolve_permission

# Maps HTTP method → resolver action
_METHOD_ACTION: dict[str, str] = {
    "GET":     "view",
    "HEAD":    "view",
    "OPTIONS": "view",
    "POST":    "create",
    "PUT":     "edit",
    "PATCH":   "edit",
    "DELETE":  "delete",
}


class HomeStackPermission(BasePermission):
    """DRF permission class backed by the central resolver.

    Override `resource` on subclasses, or use the `for_resource()` factory:
        permission_classes = [HomeStackPermission.for_resource("people")]
    """

    resource: str = ""

    def has_permission(self, request, view) -> bool:
        # Views may set `permission_action` to override the HTTP-method→action mapping.
        action = (
            getattr(view, "permission_action", None)
            or _METHOD_ACTION.get(request.method, "view")
        )
        resource = getattr(view, "resource_name", None) or self.resource
        return resolve_permission(request.user, action, resource)

    @classmethod
    def for_resource(cls, resource: str) -> type:
        """Return a concrete permission class locked to the given resource."""
        return type(f"HomeStackPermission[{resource}]", (cls,), {"resource": resource})
