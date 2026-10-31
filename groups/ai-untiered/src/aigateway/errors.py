"""Error types for the aigateway package.

Clean-room implementation. Every error raised deliberately by this
package derives from :class:`AIGatewayError`, so callers (including the
HTTP service layer) can map failures to responses without ever leaking
a stack trace.
"""


class AIGatewayError(Exception):
    """Base class for all aigateway errors."""


class ValidationError(AIGatewayError):
    """Input failed validation. Nothing was changed as a result."""


class NotFoundError(AIGatewayError):
    """A requested object does not exist."""


class PermissionDenied(AIGatewayError):
    """The actor is not permitted to perform the requested action."""


class QuotaExceeded(AIGatewayError):
    """The request would exceed the owner's monthly token quota."""


class PolicyBlocked(AIGatewayError):
    """A policy rule blocked the invocation.

    Carries the stored (blocked) request record's id as
    ``request_id`` so callers can retrieve that record.
    """

    def __init__(self, message="policy blocked", request_id=None):
        super().__init__(message)
        self.request_id = request_id
