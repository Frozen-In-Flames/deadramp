"""Error types for the erp package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`ErpError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class ErpError(Exception):
    """Base class for all erp errors."""


class ValidationError(ErpError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ErpError):
    """A requested object (for example, a person record) does not exist."""


class PermissionDenied(ErpError):
    """The actor is not permitted to perform the requested action."""
