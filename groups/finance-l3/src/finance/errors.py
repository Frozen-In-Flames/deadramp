"""Error types for the finance package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`FinanceError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class FinanceError(Exception):
    """Base class for all finance errors."""


class ValidationError(FinanceError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(FinanceError):
    """A requested object (for example, a program) does not exist."""


class PermissionDenied(FinanceError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(FinanceError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
