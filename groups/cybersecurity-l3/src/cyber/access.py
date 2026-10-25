"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec:

- ``admin``   -- {read, ingest, triage, manage_assets, manage_risks,
  assess_controls, audit_read, admin}
- ``analyst`` -- {read, ingest, triage, manage_assets, manage_risks,
  assess_controls}
- ``viewer``  -- {read}
- ``auditor`` -- {audit_read} only (High-baseline uplift: AC-5
  separation of duties -- the role that reviews the audit trail holds
  no operational permission)

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "analyst", "viewer", "auditor")

ACTIONS = (
    "read",
    "ingest",
    "triage",
    "manage_assets",
    "manage_risks",
    "assess_controls",
    "audit_read",
    "admin",
)

PERMISSIONS = {
    "admin": {
        "read",
        "ingest",
        "triage",
        "manage_assets",
        "manage_risks",
        "assess_controls",
        "audit_read",
        "admin",
    },
    "analyst": {
        "read",
        "ingest",
        "triage",
        "manage_assets",
        "manage_risks",
        "assess_controls",
    },
    "viewer": {"read"},
    "auditor": {"audit_read"},
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
