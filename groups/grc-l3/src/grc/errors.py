"""Error types for the grc package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`GrcError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class GrcError(Exception):
    """Base class for all grc errors."""


class ValidationError(GrcError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(GrcError):
    """A requested object (for example, a finding) does not exist."""


class PermissionDenied(GrcError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(GrcError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
