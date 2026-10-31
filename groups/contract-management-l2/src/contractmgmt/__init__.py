"""DeadRamp Phase 2, remainder new sibling group — Contract
Management L2 merged build.

A clean-room records substrate for the federal contract lifecycle:
organization and participant registries, contract records with a
modification bounds invariant (obligated amount never below zero
and never above the contract ceiling), compliance requirement
records, protest and data-call case records, risk records,
communication records (metadata only, never content), opportunity,
submission and award records for the acquisition portal surface,
fee and payment records in integer cents, workflow and integration
registries that record and never execute — over an append-only
audit log. Records and opaque caller-supplied references only: no
contract text, no bid contents, no message content, and nothing
about any real person is ever stored.
"""

__version__ = "0.1.0"
