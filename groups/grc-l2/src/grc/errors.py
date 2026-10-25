"""Error types for the grc package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`GrcError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class GrcError(Exception):
    """Base class for all grc errors."""


class ValidationError(GrcError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(GrcError):
    """A requested object (for example, a finding) does not exist."""


class PermissionDenied(GrcError):
    """The actor is not permitted to perform the requested action."""
