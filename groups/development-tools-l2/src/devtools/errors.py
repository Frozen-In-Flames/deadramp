"""Error types for the devtools package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`DevToolsError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class DevToolsError(Exception):
    """Base class for all devtools errors."""


class ValidationError(DevToolsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(DevToolsError):
    """A requested object does not exist."""


class PermissionDenied(DevToolsError):
    """The actor is not permitted to perform the requested action."""
