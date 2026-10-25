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


class AuditWriteError(CollabError):
    """The audit log could not durably record an entry (AU-5).

    Raised when an audit write fails; the operation being audited
    fails closed (does not proceed). The in-memory append is rolled
    back before this propagates, so an operation whose audit write
    fails does not proceed and changes nothing.
    """
