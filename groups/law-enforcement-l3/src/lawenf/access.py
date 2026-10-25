"""Role-based access control hooks.

Roles and the permission matrix are fixed by the contract:

- ``admin``  -- all actions, including ``audit_read``
- ``member`` -- all reads except ``audit_read``, plus every write
  action (``matter_write``, ``source_write``, ``document_write``,
  ``search_write``, ``annotation_write``, ``citation_write``)
- ``viewer`` -- reads only (``matter_read``, ``report_read``), never
  ``audit_read``
- ``auditor`` -- ``audit_read`` only (High-baseline uplift, AC-5
  separation of duties: audit review exists as a duty separable from
  administration; the auditor holds no registry permission at all)

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Role permission is only one of the two boundaries in this build: the
store additionally requires matter membership for every matter-scoped
operation (a platform ``admin`` is the exception). Plain-string
actors: store-level functions accept :class:`User` objects; where a
plain string is passed, it carries identity (for provenance / audit)
but no role, so there is nothing to enforce against at the store
layer -- the service layer, which knows the role registry, is
responsible for enforcement in that case. This mirrors the house
convention of the sibling groups.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "member", "viewer", "auditor")

ACTIONS = (
    "matter_read",
    "report_read",
    "audit_read",
    "matter_write",
    "source_write",
    "document_write",
    "search_write",
    "annotation_write",
    "citation_write",
)

_READS = {"matter_read", "report_read"}
_WRITES = {
    "matter_write",
    "source_write",
    "document_write",
    "search_write",
    "annotation_write",
    "citation_write",
}

PERMISSIONS = {
    "admin": set(ACTIONS),
    "member": set(_READS) | set(_WRITES),
    "viewer": set(_READS),
    "auditor": {"audit_read"},
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
