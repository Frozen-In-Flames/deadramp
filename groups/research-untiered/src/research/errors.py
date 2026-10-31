"""Error types for the research package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`ResearchError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class ResearchError(Exception):
    """Base class for all research errors."""


class ValidationError(ResearchError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ResearchError):
    """A requested object (for example, a commons) does not exist."""


class PermissionDenied(ResearchError):
    """The actor is not permitted to perform the requested action."""
