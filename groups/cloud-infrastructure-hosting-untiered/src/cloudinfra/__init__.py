"""Cloud Infrastructure & Hosting records substrate.

Clean-room implementation of the Cloud Infrastructure & Hosting L2
union spec: tenancy, environment, deployment, template, monitoring,
security-service, protection, identity-configuration, operations,
account, utilization, and recommendation records over an append-only
audit log. Records about infrastructure — the substrate provisions
nothing and operates nothing.
"""

from .access import ROLE_PERMISSIONS, ROLES, ACTIONS, User, require
from .audit import AuditLog
from .errors import (
    CloudInfraError,
    NotFoundError,
    PermissionDenied,
    ValidationError,
)
from .store import CloudInfraStore

__version__ = "0.1.0"

__all__ = [
    "ACTIONS",
    "ROLES",
    "ROLE_PERMISSIONS",
    "AuditLog",
    "CloudInfraError",
    "CloudInfraStore",
    "NotFoundError",
    "PermissionDenied",
    "User",
    "ValidationError",
    "require",
]
