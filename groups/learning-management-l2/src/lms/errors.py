"""Error types for the lms package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`LmsError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class LmsError(Exception):
    """Base class for all lms errors."""


class ValidationError(LmsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(LmsError):
    """A requested object (for example, a course) does not exist."""


class PermissionDenied(LmsError):
    """The actor is not permitted to perform the requested action."""
