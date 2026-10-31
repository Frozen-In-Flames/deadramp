"""Role-based access control hooks.

Roles and the permission matrix are fixed by the group contract
(RBAC core function):

- ``admin``     -- all actions, including ``audit_read``
- ``developer`` -- all reads + all writes + ``search`` (NOT ``audit_read``)
- ``viewer``    -- all reads + ``search`` only

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

ROLES = ("admin", "developer", "viewer")

ACTIONS = (
    "project_read",
    "project_write",
    "issue_read",
    "issue_write",
    "review_read",
    "review_write",
    "build_read",
    "build_write",
    "release_read",
    "release_write",
    "artifact_read",
    "artifact_write",
    "deployment_read",
    "deployment_write",
    "search",
    "audit_read",
)

_READS = {
    "project_read", "issue_read", "review_read", "build_read",
    "release_read", "artifact_read", "deployment_read",
}
_WRITES = {
    "project_write", "issue_write", "review_write", "build_write",
    "release_write", "artifact_write", "deployment_write",
}

PERMISSIONS = {
    "admin": set(_READS) | set(_WRITES) | {"search", "audit_read"},
    "developer": set(_READS) | set(_WRITES) | {"search"},
    "viewer": set(_READS) | {"search"},
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
