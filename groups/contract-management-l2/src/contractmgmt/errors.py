"""Error types for the contractmgmt package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`ContractMgmtError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class ContractMgmtError(Exception):
    """Base class for all contractmgmt errors."""


class ValidationError(ContractMgmtError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ContractMgmtError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(ContractMgmtError):
    """The actor is not permitted to perform the requested action."""
