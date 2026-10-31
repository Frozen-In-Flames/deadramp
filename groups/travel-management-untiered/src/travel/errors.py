"""Error types for the travel package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`TravelError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class TravelError(Exception):
    """Base class for all travel errors."""


class ValidationError(TravelError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(TravelError):
    """A requested object (for example, an authorization) does not exist."""


class PermissionDenied(TravelError):
    """The actor is not permitted to perform the requested action."""
