"""Role-based access control hooks.

Roles and the permission matrix are fixed by the union spec:

- ``admin``   -- {read, create_book, enter, submit, approve, pay,
  close, manage_members, audit_read, admin}
- ``member``  -- {read, create_book, enter, submit, approve, pay,
  close}
- ``viewer``  -- {read}
- ``auditor`` -- {audit_read} only [L3] (AC-5 separation of duties: the
  role that reviews the audit trail holds no operational permission --
  it cannot read books, enter, approve, pay, or administer)

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).
Book membership is a second, separate boundary enforced by the store
on top of this matrix.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "member", "viewer", "auditor")

ACTIONS = (
    "read",
    "create_book",
    "enter",
    "submit",
    "approve",
    "pay",
    "close",
    "manage_members",
    "audit_read",
    "admin",
)

PERMISSIONS = {
    "admin": {
        "read",
        "create_book",
        "enter",
        "submit",
        "approve",
        "pay",
        "close",
        "manage_members",
        "audit_read",
        "admin",
    },
    "member": {"read", "create_book", "enter", "submit", "approve", "pay", "close"},
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
