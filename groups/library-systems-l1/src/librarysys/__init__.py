"""Library Systems L1 merged build (DeadRamp Phase 2).

Clean-room records substrate for the Library Systems category at
CMMC L1 (FedRAMP Low / LI-SaaS), founded from the no-signal
resolution: catalogue, holdings and circulation records, integration
and workflow registries, reporting and search. Records only; no
engines."""
from .errors import LibrarySysError, NotFoundError, PermissionDenied, ValidationError
from .store import LibrarySysStore
__all__ = ["LibrarySysError", "NotFoundError", "PermissionDenied",
           "ValidationError", "LibrarySysStore"]
