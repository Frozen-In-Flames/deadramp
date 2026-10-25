"""Error types for the datamgmt package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`DataMgmtError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class DataMgmtError(Exception):
    """Base class for all datamgmt errors."""


class ValidationError(DataMgmtError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(DataMgmtError):
    """A requested object (for example, a dataset) does not exist."""


class PermissionDenied(DataMgmtError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(DataMgmtError):
    """The audit log could not durably record an entry (AU-5).

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
