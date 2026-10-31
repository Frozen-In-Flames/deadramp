"""Error types for the opsmgmt package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`OpsError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class OpsError(Exception):
    """Base class for all opsmgmt errors."""


class ValidationError(OpsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(OpsError):
    """A requested object (for example, a work order) does not exist."""


class PermissionDenied(OpsError):
    """The actor is not permitted to perform the requested action."""
