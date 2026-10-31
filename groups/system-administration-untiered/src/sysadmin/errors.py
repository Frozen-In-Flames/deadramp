"""Error types for the sysadmin package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`SysadminError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class SysadminError(Exception):
    """Base class for all sysadmin errors."""


class ValidationError(SysadminError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(SysadminError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(SysadminError):
    """The actor is not permitted to perform the requested action."""
