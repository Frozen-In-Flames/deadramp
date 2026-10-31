"""Error types for the marketsales package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`MarketSalesError`, so callers
(including the HTTP service layer) can map failures to responses
without ever leaking a stack trace.
"""


class MarketSalesError(Exception):
    """Base class for all marketsales errors."""


class ValidationError(MarketSalesError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(MarketSalesError):
    """A requested object (for example, a campaign) does not exist."""


class PermissionDenied(MarketSalesError):
    """The actor is not permitted to perform the requested action."""
