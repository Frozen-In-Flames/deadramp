"""Role-based access control hooks.

Roles and the permission matrix are fixed by the contract:

- ``admin``  -- all actions
- ``agent``  -- all reads except ``audit_read``, plus ``case_write``,
  ``requester_write``, ``responder_write``, ``alert_write`` and
  ``schedule_write`` (NOT ``rule_write``, NOT ``audit_read``)
- ``viewer`` -- reads only, except ``audit_read``
- ``auditor``  -- ``audit_read`` only [L3] (AC-5 separation of duties:
  the role that reviews the audit trail holds no operational
  permission -- it cannot read cases, requesters, responders,
  alerts, schedules, rules or reports, and cannot write anything)

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the role
registry, is responsible for enforcement in that case. This mirrors
the contact-center group's convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "agent", "viewer", "auditor")

ACTIONS = (
    "case_read",
    "requester_read",
    "responder_read",
    "alert_read",
    "schedule_read",
    "rule_read",
    "report_read",
    "audit_read",
    "case_write",
    "requester_write",
    "responder_write",
    "alert_write",
    "schedule_write",
    "rule_write",
)

_ALL_READS = {
    "case_read",
    "requester_read",
    "responder_read",
    "alert_read",
    "schedule_read",
    "rule_read",
    "report_read",
}
_AGENT_WRITES = {
    "case_write",
    "requester_write",
    "responder_write",
    "alert_write",
    "schedule_write",
}

PERMISSIONS = {
    "admin": set(_ALL_READS) | set(_AGENT_WRITES) | {"rule_write", "audit_read"},
    "agent": set(_ALL_READS) | set(_AGENT_WRITES),
    "viewer": set(_ALL_READS),
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
