"""Error types for the hr package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`HRError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class HRError(Exception):
    """Base class for all hr errors."""


class ValidationError(HRError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(HRError):
    """A requested object (for example, a person) does not exist."""


class PermissionDenied(HRError):
    """The actor is not permitted to perform the requested action."""
