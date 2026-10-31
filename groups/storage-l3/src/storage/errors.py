"""Error types for the storage package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`StorageError`, so callers (including
the HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class StorageError(Exception):
    """Base class for all storage errors."""


class ValidationError(StorageError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(StorageError):
    """A requested object (for example, a collection) does not exist."""


class PermissionDenied(StorageError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(StorageError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
