"""Error types for the mdm package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`MdmError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class MdmError(Exception):
    """Base class for all mdm errors."""


class ValidationError(MdmError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(MdmError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(MdmError):
    """The actor is not permitted to perform the requested action."""
