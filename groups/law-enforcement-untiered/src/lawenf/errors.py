"""Error types for the lawenf package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`LawEnfError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class LawEnfError(Exception):
    """Base class for all lawenf errors."""


class ValidationError(LawEnfError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(LawEnfError):
    """A requested object (for example, a matter) does not exist."""


class PermissionDenied(LawEnfError):
    """The actor is not permitted to perform the requested action."""
