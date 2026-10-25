"""Error types for the custsvc package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CustsvcError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CustsvcError(Exception):
    """Base class for all custsvc errors."""


class ValidationError(CustsvcError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CustsvcError):
    """A requested object (for example, a case) does not exist."""


class PermissionDenied(CustsvcError):
    """The actor is not permitted to perform the requested action."""
