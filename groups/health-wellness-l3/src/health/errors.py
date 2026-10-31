"""Error types for the health package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`HealthError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class HealthError(Exception):
    """Base class for all health errors."""


class ValidationError(HealthError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(HealthError):
    """A requested object (for example, a participant) does not exist."""


class PermissionDenied(HealthError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(HealthError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
