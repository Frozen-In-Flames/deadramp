"""Error types for the grants package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`GrantsError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class GrantsError(Exception):
    """Base class for all grants errors."""


class ValidationError(GrantsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(GrantsError):
    """A requested object (for example, a program) does not exist."""


class PermissionDenied(GrantsError):
    """The actor is not permitted to perform the requested action."""
