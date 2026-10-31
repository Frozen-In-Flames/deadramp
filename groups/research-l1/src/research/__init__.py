"""Research L1 — singleton clean-room build (Operation DeadRamp,
Phase 2 remainder, Research L1 singleton).

A records substrate for research data commons: commons, ecosystems
and meshes, organizations as opaque references, workspaces, datasets
as metadata plus SHA-256 checksums only, access requests, decisions,
and time-boxed access grants whose status is derived at read and
never stored, at the FedRAMP Low (LI-SaaS) / CMMC L1 baseline. The
implementation is the Research L2 build's substrate carried down
whole (see this group's UNION-SPEC.md); only this docstring differs
from the parent build.
Python standard library only.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
