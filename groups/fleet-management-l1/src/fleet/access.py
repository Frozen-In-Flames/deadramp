"""Role-based access control hooks.

Roles and the permission matrix are fixed by the group contract
(RBAC core function). Every role holds the baseline actions ``read``
and ``search``; on top of that baseline:

- ``admin``   -- baseline + ``write``, ``audit_read``, ``admin``
- ``manager`` -- baseline + ``write``
- ``viewer``  -- baseline only (read + search only; no writes)

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the role
registry, is responsible for enforcement in that case.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "manager", "viewer")

ACTIONS = ("read", "write", "search", "audit_read", "admin")

_BASELINE = {"read", "search"}

PERMISSIONS = {
    "admin": set(_BASELINE) | {"write", "audit_read", "admin"},
    "manager": set(_BASELINE) | {"write"},
    "viewer": set(_BASELINE),
}


@dataclass(frozen=True)
class User:
    """An authenticated identity as supplied by the embedding system."""

    name: str
    role: str


def permissions_for(role):
    """Return the permission set for ``role`` (empty set if unknown)."""
    return PERMISSIONS.get(role, set())


def can(user, action):
    """Return True if ``user`` may perform ``action``."""
    if user is None:
        return False
    role = getattr(user, "role", None)
    return action in PERMISSIONS.get(role, set())


def require(user, action):
    """Raise :class:`PermissionDenied` unless ``user`` may do ``action``."""
    if user is None:
        raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    name = getattr(user, "name", None)
    role = getattr(user, "role", None)
    if role not in PERMISSIONS or action not in PERMISSIONS[role]:
        raise PermissionDenied(
            "permission denied: user %r with role %r may not perform %r"
            % (name, role, action)
        )
    return True
