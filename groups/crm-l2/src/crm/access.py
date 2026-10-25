"""Role-based access control hooks.

Roles and the permission matrix are fixed by the contract:

- ``admin``    -- all actions
- ``operator`` -- all reads except ``audit_read``, plus
  ``registry_write``, ``case_write``, ``interaction_write``,
  ``guide_write``, ``finding_write`` (NOT ``config_write``,
  NOT ``audit_read``)
- ``viewer``   -- reads only, except ``audit_read``

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user
registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the
role registry, is responsible for enforcement in that case. This
mirrors the shipped groups' convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "operator", "viewer")

ACTIONS = (
    "registry_read",
    "case_read",
    "interaction_read",
    "guide_read",
    "finding_read",
    "config_read",
    "report_read",
    "audit_read",
    "registry_write",
    "case_write",
    "interaction_write",
    "guide_write",
    "finding_write",
    "config_write",
)

_ALL_READS = {
    "registry_read",
    "case_read",
    "interaction_read",
    "guide_read",
    "finding_read",
    "config_read",
    "report_read",
}
_OPERATOR_WRITES = {
    "registry_write",
    "case_write",
    "interaction_write",
    "guide_write",
    "finding_write",
}

PERMISSIONS = {
    "admin": set(_ALL_READS) | set(_OPERATOR_WRITES) | {"config_write", "audit_read"},
    "operator": set(_ALL_READS) | set(_OPERATOR_WRITES),
    "viewer": set(_ALL_READS),
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
    """Raise :class:`PermissionDenied` unless ``user`` may do ``action``.

    ``user`` is expected to be a :class:`User` (or any object with
    ``name`` / ``role`` attributes). Unknown users, unknown roles and
    actions outside the role's permission set are all denied.
    """
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
