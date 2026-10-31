"""Error types for the events package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`EventsError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class EventsError(Exception):
    """Base class for all events errors."""


class ValidationError(EventsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(EventsError):
    """A requested object (for example, an event) does not exist."""


class PermissionDenied(EventsError):
    """The actor is not permitted to perform the requested action."""
