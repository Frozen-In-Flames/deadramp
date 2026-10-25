"""Error types for the comm package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CommError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CommError(Exception):
    """Base class for all comm errors."""


class ValidationError(CommError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CommError):
    """A requested object (for example, a contact) does not exist."""


class PermissionDenied(CommError):
    """The actor is not permitted to perform the requested action."""
