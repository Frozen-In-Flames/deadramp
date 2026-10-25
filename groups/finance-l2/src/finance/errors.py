"""Error types for the finance package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`FinanceError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class FinanceError(Exception):
    """Base class for all finance errors."""


class ValidationError(FinanceError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(FinanceError):
    """A requested object (for example, a program) does not exist."""


class PermissionDenied(FinanceError):
    """The actor is not permitted to perform the requested action."""
