"""Error types for the construct package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`ConstructError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class ConstructError(Exception):
    """Base class for all construct errors."""


class ValidationError(ConstructError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ConstructError):
    """A requested object (for example, a project) does not exist."""


class PermissionDenied(ConstructError):
    """The actor is not permitted to perform the requested action."""
