"""Error types for the media package.

Clean-room implementation. Every error raised deliberately by
this package derives from :class:`MediaError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class MediaError(Exception):
    """Base class for all media errors."""


class ValidationError(MediaError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(MediaError):
    """A requested object (for example, a route) does not exist."""


class PermissionDenied(MediaError):
    """The actor is not permitted to perform the requested action."""
