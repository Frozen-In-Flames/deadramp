# Operation DeadRamp

Every FedRAMP vendor, open sourced. One collective repo, one fork per vendor, merges governed by NIST.

## What this is

The FedRAMP Marketplace is a public index of the cloud services and products the United States government is authorized to buy. Vendors charge premium prices behind that compliance gate. DeadRamp takes the map the government already publishes and builds the open version of the territory:

- **Index.** Every FedRAMP-authorized vendor and product, registered from public marketplace data.
- **Spec.** Each service modeled from its public surface: documentation, public APIs, and the open standards underneath it.
- **Build.** Clean-room open-source equivalents, one fork per vendor, under one collective repo. Incumbent methods are studied and implemented; no proprietary code is copied.
- **Compliance as shared infrastructure.** The control baselines (NIST SP 800-53) and the CMMC practice sets are public. In DeadRamp they are the shared skeleton every fork hangs on, not a per-vendor toll.

## The two axes

Every fork is placed on two axes:

1. **Function** — what it does: service category and model (IaaS, PaaS, SaaS).
2. **Trust tier** — who may rely on it and at what assurance, matched by CMMC level. FedRAMP Low sits at the CMMC Level 1 tier, FedRAMP Moderate at Level 2 (the NIST SP 800-171 substrate), FedRAMP High at Level 3-adjacent. FedRAMP authorizes products and CMMC certifies organizations, so the tier is a matching equivalence for planning, never a claim that a credential transfers.

Forks with the same function and the same tier are siblings: true substitutes. Forks chain into stacks: IaaS under PaaS under SaaS.

## The merge rule

Merges are NIST compliant by construction:

- A merge takes the **union** of the parent forks' control baselines, never the intersection. Merging cannot dilute a control.
- The merged fork inherits the **highest** tier of its parents and must satisfy that tier in full.
- Every merge carries **control traceability**: which parent contributed which controls, auditable from the record.
- The merge process follows NIST SP 800-218 (SSDF): provenance, review, and verification before a merge lands.

Compliance only ratchets one direction. Up.

## Status

Phase 1 in progress: the complete fork map (registry, CMMC crosswalk, sibling and stack relations) built from public FedRAMP Marketplace data, with an honest coverage note. See CONCEPT.md for the full design.

## License

Apache-2.0. Copyright 2026 Aries Hilton.
