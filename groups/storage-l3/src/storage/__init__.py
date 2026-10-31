"""Storage L3-adjacent — singleton clean-room build (Operation
DeadRamp, Phase 2 remainder).

A records substrate for message archiving storage: organization,
retention-policy, and archive-collection registries keyed by
opaque references; message archive records holding metadata only
(no payloads, no content); retention state derived at read with a
gated disposition; discovery, supervision, enforcement, retrieval,
key-custody, and integration records — carried up whole from the
Storage L2 build and uplifted to the FedRAMP High / CMMC
L3-adjacent baseline (hash-chained, fail-closed, queryable audit;
auditor role; logon lockout). Python standard library only.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
