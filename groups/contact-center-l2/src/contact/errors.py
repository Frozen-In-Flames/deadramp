"""Error types for the contact package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`ContactError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class ContactError(Exception):
    """Base class for all contact errors."""


class ValidationError(ContactError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(ContactError):
    """A requested object (for example, a case) does not exist."""


class PermissionDenied(ContactError):
    """The actor is not permitted to perform the requested action."""
