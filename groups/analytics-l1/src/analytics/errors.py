"""Error types for the analytics package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`AnalyticsError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking a
stack trace.
"""


class AnalyticsError(Exception):
    """Base class for all analytics errors."""


class ValidationError(AnalyticsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(AnalyticsError):
    """A requested object (for example, a dataset) does not exist."""


class PermissionDenied(AnalyticsError):
    """The actor is not permitted to perform the requested action."""
