"""Error types for the comm package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CommError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CommError(Exception):
    """Base class for all comm errors."""


class ValidationError(CommError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CommError):
    """A requested object (for example, a contact) does not exist."""


class PermissionDenied(CommError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(CommError):
    """The audit log could not durably record an entry (AU-5).

    Raised when an audit write fails; the operation being audited
    fails closed (does not proceed). The in-memory append is rolled
    back before this propagates, so an operation whose audit write
    fails does not proceed and changes nothing.
    """
