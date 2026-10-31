"""Error types for the manufacturing package.

Clean-room implementation. Every error raised deliberately by
this package derives from :class:`ManufacturingError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class ManufacturingError(Exception):
    """Base class for all manufacturing errors."""


class ValidationError(ManufacturingError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ManufacturingError):
    """A requested object (for example, an intent record) does not
    exist."""


class PermissionDenied(ManufacturingError):
    """The actor is not permitted to perform the requested action."""
