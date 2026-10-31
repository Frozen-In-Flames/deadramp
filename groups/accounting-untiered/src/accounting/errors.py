"""Error types for the accounting package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`AccountingError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class AccountingError(Exception):
    """Base class for all accounting errors."""


class ValidationError(AccountingError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(AccountingError):
    """A requested object (for example, a book) does not exist."""


class PermissionDenied(AccountingError):
    """The actor is not permitted to perform the requested action."""
