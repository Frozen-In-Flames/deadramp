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
