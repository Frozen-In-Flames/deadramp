"""Error types for the talentmgmt package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`TalentMgmtError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class TalentMgmtError(Exception):
    """Base class for all talentmgmt errors."""


class ValidationError(TalentMgmtError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(TalentMgmtError):
    """A requested object (for example, an organization) does not exist."""


class PermissionDenied(TalentMgmtError):
    """The actor is not permitted to perform the requested action."""
