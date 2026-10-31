"""Cloud Infrastructure & Hosting records substrate.

Clean-room implementation of the Cloud Infrastructure & Hosting
union spec at the High tier (L3-adjacent): the founding L2 core
carried up whole — tenancy, environment, deployment, template,
monitoring, security-service, protection, identity-configuration,
operations, account, utilization, and recommendation records —
over a hash-chained, fail-closed audit log [L3]. Records about
infrastructure — the substrate provisions nothing and operates
nothing.
"""

from .access import ROLE_PERMISSIONS, ROLES, ACTIONS, User, require
from .audit import AuditLog
from .errors import (
    AuditWriteError,
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
    "AuditWriteError",
    "CloudInfraError",
    "CloudInfraStore",
    "NotFoundError",
    "PermissionDenied",
    "User",
    "ValidationError",
    "require",
]
