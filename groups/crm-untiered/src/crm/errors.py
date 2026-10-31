"""Error types for the crm package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CrmError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class CrmError(Exception):
    """Base class for all crm errors."""


class ValidationError(CrmError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CrmError):
    """A requested object (for example, a case) does not exist."""


class PermissionDenied(CrmError):
    """The actor is not permitted to perform the requested action."""
