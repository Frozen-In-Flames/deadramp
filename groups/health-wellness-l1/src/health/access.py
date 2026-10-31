"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec (Core
function 9, RBAC):

- ``admin``     -- all actions, including ``audit_read``
- ``clinician`` -- all 7 record reads plus ``enrollment_write``,
  ``measurement_write``, ``plan_write`` and ``activity_write``, plus
  ``report_read``
- ``member``    -- the 7 record reads only (own-participant scope;
  member scope is enforced in the store), no writes, no
  ``report_read``, no ``audit_read``
- ``auditor``   -- all 7 record reads plus ``report_read`` and
  ``audit_read``; no writes

RBAC is baseline-carried, not claimed: 0/5 siblings describe RBAC in
functional terms; it is Core because the L2/Moderate baseline requires
it (see UNION-SPEC.md).

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the role
registry, is responsible for enforcement in that case. This mirrors
the education group's convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "clinician", "member", "auditor")

ACTIONS = (
    "participant_read",
    "participant_write",
    "program_read",
    "program_write",
    "enrollment_read",
    "enrollment_write",
    "measurement_read",
    "measurement_write",
    "plan_read",
    "plan_write",
    "activity_read",
    "activity_write",
    "eligibility_read",
    "eligibility_write",
    "report_read",
    "audit_read",
)

_RECORD_READS = {
    "participant_read",
    "program_read",
    "enrollment_read",
    "measurement_read",
    "plan_read",
    "activity_read",
    "eligibility_read",
}
_CLINICIAN_WRITES = {
    "enrollment_write",
    "measurement_write",
    "plan_write",
    "activity_write",
}
_ALL_WRITES = {
    "participant_write",
    "program_write",
    "enrollment_write",
    "measurement_write",
    "plan_write",
    "activity_write",
    "eligibility_write",
}

PERMISSIONS = {
    "admin": set(_RECORD_READS) | set(_ALL_WRITES) | {"report_read", "audit_read"},
    "clinician": set(_RECORD_READS) | set(_CLINICIAN_WRITES) | {"report_read"},
    "member": set(_RECORD_READS),
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
