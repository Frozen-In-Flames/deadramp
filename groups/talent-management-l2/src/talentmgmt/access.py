"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec:

- ``admin``  -- all eleven actions, including ``audit_read``
- ``member`` -- all except ``org_write`` and ``audit_read``
- ``viewer`` -- {``org_read``, ``report_read``} only

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user
registry). Organization membership is a second, separate boundary
enforced by the store on top of this matrix. Plain-string actors
carry identity (for provenance / audit) but no role, so role
enforcement for those happens in the service layer -- the house
convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "member", "viewer")

ACTIONS = (
    "org_read",
    "org_write",
    "candidate_write",
    "requisition_write",
    "pipeline_write",
    "event_write",
    "assessment_write",
    "interview_write",
    "registry_write",
    "report_read",
    "audit_read",
)

PERMISSIONS = {
    "admin": set(ACTIONS),
    "member": set(ACTIONS) - {"org_write", "audit_read"},
    "viewer": {"org_read", "report_read"},
}


@dataclass(frozen=True)
class User:
    """An actor with a platform role."""

    name: str
    role: str

    def __post_init__(self):
        if self.role not in PERMISSIONS:
            raise PermissionDenied("unknown role: %r" % (self.role,))


def permissions_for(role):
    """Return the permission set for a role (a copy)."""
    if role not in PERMISSIONS:
        raise PermissionDenied("unknown role: %r" % (role,))
    return set(PERMISSIONS[role])


def can(user, action):
    """True when the user's role permits the action."""
    if action not in ACTIONS:
        return False
    return action in PERMISSIONS.get(getattr(user, "role", None), set())


def require(user, action):
    """Raise PermissionDenied unless the user's role permits the action."""
    if action not in ACTIONS:
        raise PermissionDenied("unknown action: %r" % (action,))
    if not can(user, action):
        raise PermissionDenied(
            "role %r may not perform %r" % (getattr(user, "role", None), action)
        )
