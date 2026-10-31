"""Error types for the crm package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CrmError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class CrmError(Exception):
    """Base class for all crm errors."""


class ValidationError(CrmError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CrmError):
    """A requested object (for example, a case) does not exist."""


class PermissionDenied(CrmError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(CrmError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
