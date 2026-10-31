"""Error types for the cloudinfra package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`CloudInfraError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class CloudInfraError(Exception):
    """Base class for all cloudinfra errors."""


class ValidationError(CloudInfraError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(CloudInfraError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(CloudInfraError):
    """The actor is not permitted to perform the requested action."""


class AuditWriteError(CloudInfraError):
    """The audit log could not durably record an entry (AU-5) [L3].

    Raised by ``AuditLog.record`` when the JSONL append fails. The
    in-memory append is rolled back before this propagates, so callers
    fail closed: an operation whose audit write fails does not proceed.
    """
