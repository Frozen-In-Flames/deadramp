"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec:

- ``admin``      -- all actions, including ``audit_read``
- ``instructor`` -- all record reads, plus the instructor write
  actions and ``report_read``; no ``audit_read``
- ``learner``    -- record reads only (own records; learner-scope is
  enforced in the store), no writes, no ``report_read``, no
  ``audit_read``
- ``auditor``    -- all record reads plus ``report_read`` and
  ``audit_read``; no writes

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the role
registry, is responsible for enforcement in that case. This mirrors
the communication group's convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "instructor", "learner", "auditor")

ACTIONS = (
    "catalog_read",
    "catalog_write",
    "learner_read",
    "learner_write",
    "registration_read",
    "registration_write",
    "authorization_read",
    "authorization_write",
    "plan_read",
    "plan_write",
    "competency_read",
    "competency_write",
    "progress_read",
    "progress_write",
    "experience_read",
    "experience_write",
    "compliance_read",
    "compliance_write",
    "workflow_read",
    "workflow_write",
    "report_read",
    "audit_read",
)

_RECORD_READS = {
    "catalog_read",
    "learner_read",
    "registration_read",
    "authorization_read",
    "plan_read",
    "competency_read",
    "progress_read",
    "experience_read",
    "compliance_read",
    "workflow_read",
}
_INSTRUCTOR_WRITES = {
    "registration_write",
    "authorization_write",
    "plan_write",
    "competency_write",
    "progress_write",
    "experience_write",
    "workflow_write",
}
_ALL_WRITES = set(_INSTRUCTOR_WRITES) | {
    "catalog_write",
    "learner_write",
    "compliance_write",
}

PERMISSIONS = {
    "admin": set(_RECORD_READS) | set(_ALL_WRITES) | {"report_read", "audit_read"},
    "instructor": set(_RECORD_READS) | set(_INSTRUCTOR_WRITES) | {"report_read"},
    "learner": set(_RECORD_READS),
    "auditor": set(_RECORD_READS) | {"report_read", "audit_read"},
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
