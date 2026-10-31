"""Error types for the cms package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CmsError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class CmsError(Exception):
    """Base class for all cms errors."""


class ValidationError(CmsError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CmsError):
    """A requested object (for example, a content item) does not exist."""


class PermissionDenied(CmsError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(CmsError):
    """The audit log could not durably record an entry (AU-5). [L3]

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
