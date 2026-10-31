"""Error types for the legalpol package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`LegalPolError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class LegalPolError(Exception):
    """Base class for all legalpol errors."""


class ValidationError(LegalPolError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(LegalPolError):
    """A requested object (for example, an agency) does not exist."""


class PermissionDenied(LegalPolError):
    """The actor is not permitted to perform the requested action."""
