"""Visibility queryset mixin (D10, Architecture §7).

apply_visibility(queryset, user) filters a queryset to rows the user may see,
combining role, visibility field, and child-account safety.

Phase 1.8: extended to filter models that carry `visibility` (and optionally
`sensitivity`) fields — introduced by Atlas. Models without those fields pass
through unchanged.

Visibility matrix
-----------------
admin / manager  : see all visibility levels
user             : see 'household' + own 'private' (created_by = self)
guest            : see 'household' only
child account    : see 'household' only, never 'sensitive' sensitivity
"""
from __future__ import annotations

from django.db.models import Q, QuerySet


def _model_has_field(model, field_name: str) -> bool:
    try:
        model._meta.get_field(field_name)
        return True
    except Exception:
        return False


def apply_visibility(queryset: QuerySet, user) -> QuerySet:
    """Filter queryset to records the given user may see."""
    if not _model_has_field(queryset.model, "visibility"):
        return queryset

    is_child = getattr(user, "is_child_account", False)
    role = getattr(user, "role", "guest")

    if role in ("admin", "manager") and not is_child:
        pass  # admin/manager see all visibility levels
    elif role == "user" and not is_child:
        queryset = queryset.filter(
            Q(visibility="household")
            | Q(visibility="private", created_by=user)
        )
    else:
        # guest or child: household-visible only
        queryset = queryset.filter(visibility="household")

    # Children cannot see sensitive content regardless of visibility setting.
    if is_child and _model_has_field(queryset.model, "sensitivity"):
        queryset = queryset.exclude(sensitivity="sensitive")

    return queryset
