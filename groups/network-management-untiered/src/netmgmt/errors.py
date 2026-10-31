"""Error types for the netmgmt package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`NetmgmtError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class NetmgmtError(Exception):
    """Base class for all netmgmt errors."""


class ValidationError(NetmgmtError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(NetmgmtError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(NetmgmtError):
    """The actor is not permitted to perform the requested action."""
