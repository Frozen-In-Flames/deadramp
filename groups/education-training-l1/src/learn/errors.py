"""Error types for the learn package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`LearnError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class LearnError(Exception):
    """Base class for all learn errors."""


class ValidationError(LearnError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(LearnError):
    """A requested object (for example, a course) does not exist."""


class PermissionDenied(LearnError):
    """The actor is not permitted to perform the requested action."""
