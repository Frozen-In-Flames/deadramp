"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec:

- ``admin``  -- all eight actions
- ``member`` -- {read, registry_write, invoke, eval_run, usage_read}
- ``viewer`` -- {read, usage_read}

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "member", "viewer")

ACTIONS = (
    "read",
    "registry_write",
    "invoke",
    "eval_run",
    "usage_read",
    "policy_write",
    "audit_read",
    "admin",
)

PERMISSIONS = {
    "admin": {
        "read",
        "registry_write",
        "invoke",
        "eval_run",
        "usage_read",
        "policy_write",
        "audit_read",
        "admin",
    },
    "member": {"read", "registry_write", "invoke", "eval_run", "usage_read"},
    "viewer": {"read", "usage_read"},
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
