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

Phase 1 complete: the full fork map (781 offerings, 674 vendors) is in forks.json, MAP.md, and crosswalk.md.

Phase 2 in progress, coverage 358 of 781 forks: Group 1, Analytics L2 (128 forks), Group 2, Collaboration L2 (57 forks), Group 3, Analytics L3-adjacent (54 forks, the L2 analytics core uplifted to the High baseline), Group 4, Cybersecurity & Risk Management L2 (54 forks, the defensive substrate), Group 5, Accounting L2 (21 forks, double-entry core), Group 7, Analytics L1 (16 forks, the lightest baseline), Group 6, Collaboration L3-adjacent (17 forks, the L2 collaboration core uplifted to High), and Group 9, Artificial Intelligence (AI) L2 (11 forks, the platform layer around models), are spec'd (one sheet per fork, every claim evidenced), merged under the Merge Rule, and their common cores are built and tested in groups/analytics-l2/ (136 tests), groups/collaboration-l2/ (192 tests), groups/analytics-l3/ (183 tests), groups/cybersecurity-l2/ (194 tests), and groups/accounting-l2/ (219 tests), groups/analytics-l1/ (136 tests), groups/collaboration-l3/ (239 tests), and groups/ai-l2/ (146 tests), each with mutation-verified negative controls. Fourteen extended functions from the group's union spec are specified but not yet implemented; they are listed in the group's UNION-SPEC.md. See CONCEPT.md for the design and PIPELINE.md for the build order.

## License

Apache-2.0. Copyright 2026 Aries Hilton.
