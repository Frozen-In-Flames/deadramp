"""Error types for the cyber package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CyberError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class CyberError(Exception):
    """Base class for all cyber errors."""


class ValidationError(CyberError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CyberError):
    """A requested object (for example, an asset) does not exist."""


class PermissionDenied(CyberError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(CyberError):
    """The audit log could not durably record an entry (AU-5).

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
