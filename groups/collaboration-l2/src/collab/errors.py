"""Error types for the collab package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CollabError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CollabError(Exception):
    """Base class for all collab errors."""


class ValidationError(CollabError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CollabError):
    """A requested object (for example, a workspace) does not exist."""


class PermissionDenied(CollabError):
    """The actor is not permitted to perform the requested action."""
