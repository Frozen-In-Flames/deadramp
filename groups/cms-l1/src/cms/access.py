"""Role-based access control hooks.

Roles and the permission matrix are fixed by the contract:

- ``admin``     -- all actions
- ``publisher`` -- all reads except audit_read, plus all writes
- ``editor``    -- all reads except audit_read, plus section_write,
  item_create, item_edit, item_submit, item_review, asset_write and
  tag_write
- ``author``    -- all reads except audit_read, plus item_create,
  item_edit, item_submit and asset_write (item_edit / item_submit for
  an author are additionally limited to the author's OWN items --
  that ownership rule is enforced in the store, which knows the item)
- ``viewer``    -- all reads except audit_read, no writes

These are enforcement hooks, not an identity provider: the embedding
organization supplies identity (see the service layer's user registry).

Plain-string actors: store-level functions accept :class:`User`
objects; where a plain string is passed, it carries identity (for
provenance / audit) but no role, so there is nothing to enforce
against at the store layer -- the service layer, which knows the role
registry, is responsible for enforcement in that case. This mirrors
the data-management group's convention.
"""

from dataclasses import dataclass

from .errors import PermissionDenied

ROLES = ("admin", "publisher", "editor", "author", "viewer")

ACTIONS = (
    "site_read",
    "section_read",
    "type_read",
    "item_read",
    "asset_read",
    "tag_read",
    "search",
    "report_read",
    "site_write",
    "section_write",
    "type_write",
    "item_create",
    "item_edit",
    "item_submit",
    "item_review",
    "item_publish",
    "item_archive",
    "asset_write",
    "tag_write",
    "audit_read",
)

_READS = {
    "site_read",
    "section_read",
    "type_read",
    "item_read",
    "asset_read",
    "tag_read",
    "search",
    "report_read",
}
_PUBLISHER_WRITES = {
    "site_write",
    "section_write",
    "type_write",
    "item_create",
    "item_edit",
    "item_submit",
    "item_review",
    "item_publish",
    "item_archive",
    "asset_write",
    "tag_write",
}
_EDITOR_WRITES = {
    "section_write",
    "item_create",
    "item_edit",
    "item_submit",
    "item_review",
    "asset_write",
    "tag_write",
}
_AUTHOR_WRITES = {
    "item_create",
    "item_edit",
    "item_submit",
    "asset_write",
}

PERMISSIONS = {
    "admin": set(_READS) | set(_PUBLISHER_WRITES) | {"audit_read"},
    "publisher": set(_READS) | set(_PUBLISHER_WRITES),
    "editor": set(_READS) | set(_EDITOR_WRITES),
    "author": set(_READS) | set(_AUTHOR_WRITES),
    "viewer": set(_READS),
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
