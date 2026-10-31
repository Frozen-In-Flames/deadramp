"""Role-based access control for the cloudinfra package.

Four roles:

- ``admin``: every action, including organization administration
  (``org_write``) and audit reads (``audit_read``).
- ``member``: every working action (``org_read``, ``tenancy_write``,
  ``environment_write``, ``provider_write``, ``deployment_write``,
  ``template_write``, ``service_write``, ``operations_write``,
  ``report_read``), but not ``org_write`` or ``audit_read``.
- ``viewer``: ``org_read`` and ``report_read`` only.
- ``auditor``: ``audit_read`` only [L3] (AC-5 separation of duties:
  the role that reviews the audit trail holds no operational
  permission — it cannot read organizations or records, and cannot
  write anything). This role is a High-baseline uplift; the
  founding L2 build has three roles and makes no AC-5 claim.

Membership is a second, independent boundary enforced by the
store: org-scoped record operations require the actor to belong to
the organization (or be an admin) regardless of role.
"""

from .errors import PermissionDenied

ACTIONS = (
    "org_read",
    "org_write",
    "tenancy_write",
    "environment_write",
    "provider_write",
    "deployment_write",
    "template_write",
    "service_write",
    "operations_write",
    "report_read",
    "audit_read",
)

ROLE_PERMISSIONS = {
    "admin": frozenset(ACTIONS),
    "member": frozenset(
        action
        for action in ACTIONS
        if action not in ("org_write", "audit_read")
    ),
    "viewer": frozenset({"org_read", "report_read"}),
    "auditor": frozenset({"audit_read"}),
}

ROLES = tuple(ROLE_PERMISSIONS)


class User:
    """An authenticated principal with a role.

    ``User`` objects are what the store and service layers expect as
    the *actor* for an operation once identity is established; the
    demo identities in the CLI are hooks for the embedding
    organization's real identity system (IA-2), not an IdP.
    """

    def __init__(self, name, role):
        if role not in ROLE_PERMISSIONS:
            raise ValueError("unknown role: %r" % (role,))
        self.name = name
        self.role = role

    def __repr__(self):  # pragma: no cover - debugging aid
        return "User(%r, %r)" % (self.name, self.role)

    def can(self, action):
        return action in ROLE_PERMISSIONS[self.role]


def require(user, action):
    """Raise :class:`PermissionDenied` unless ``user`` may do ``action``."""
    if action not in ACTIONS:
        raise ValueError("unknown action: %r" % (action,))
    if not isinstance(user, User):
        raise PermissionDenied("an authenticated user is required")
    if not user.can(action):
        raise PermissionDenied(
            "user %r with role %r may not perform %r"
            % (user.name, user.role, action)
        )
