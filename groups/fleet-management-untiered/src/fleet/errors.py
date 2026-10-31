"""Error types for the fleet package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`FleetError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class FleetError(Exception):
    """Base class for all fleet errors."""


class ValidationError(FleetError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(FleetError):
    """A requested object does not exist."""


class PermissionDenied(FleetError):
    """The actor is not permitted to perform the requested action."""
