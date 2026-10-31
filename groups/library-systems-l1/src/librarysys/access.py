"""Role-based access control hooks (hooks, not an IdP)."""
from dataclasses import dataclass
from .errors import PermissionDenied
ROLES = ("admin", "member", "viewer")
ACTIONS = ("lib_read","lib_write","catalogue_write","circulation_write","registry_write","report_read","audit_read")
PERMISSIONS = {
 "admin": set(ACTIONS),
 "member": {"lib_read","catalogue_write","circulation_write","registry_write","report_read"},
 "viewer": {"lib_read","report_read"},
}
@dataclass(frozen=True)
class User:
    name: str
    role: str
def permissions_for(role):
    return PERMISSIONS.get(role, set())
def can(user, action):
    if user is None: return False
    return action in PERMISSIONS.get(getattr(user,"role",None), set())
def require(user, action):
    if user is None: raise PermissionDenied("permission denied: no user supplied for %r" % (action,))
    role = getattr(user,"role",None)
    if role not in PERMISSIONS or action not in PERMISSIONS[role]:
        raise PermissionDenied("permission denied: user %r with role %r may not perform %r" % (getattr(user,"name",None), role, action))
    return True
