"""Error types for the talentdev package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`TalentDevError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class TalentDevError(Exception):
    """Base class for all talentdev errors."""


class ValidationError(TalentDevError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(TalentDevError):
    """A requested object (for example, a program) does not exist."""


class PermissionDenied(TalentDevError):
    """The actor is not permitted to perform the requested action."""
