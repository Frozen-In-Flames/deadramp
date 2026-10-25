"""Error types for the cyber package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CyberError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CyberError(Exception):
    """Base class for all cyber errors."""


class ValidationError(CyberError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CyberError):
    """A requested object (for example, an asset) does not exist."""


class PermissionDenied(CyberError):
    """The actor is not permitted to perform the requested action."""
