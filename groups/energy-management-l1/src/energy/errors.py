"""Error types for the energy package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`EnergyError`, so callers (including the
HTTP service layer) can map failures to responses without ever
leaking a stack trace.
"""


class EnergyError(Exception):
    """Base class for all energy errors."""


class ValidationError(EnergyError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(EnergyError):
    """A requested object (for example, an auction) does not exist."""


class PermissionDenied(EnergyError):
    """The actor is not permitted to perform the requested action."""
