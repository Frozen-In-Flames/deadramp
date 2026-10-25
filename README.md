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

Phase 2 in progress, coverage 467 of 781 forks: Group 1, Analytics L2 (128 forks), Group 2, Collaboration L2 (57 forks), Group 3, Analytics L3-adjacent (54 forks, the L2 analytics core uplifted to the High baseline), Group 4, Cybersecurity & Risk Management L2 (54 forks, the defensive substrate), Group 5, Accounting L2 (21 forks, double-entry core), Group 7, Analytics L1 (16 forks, the lightest baseline), Group 6, Collaboration L3-adjacent (17 forks, the L2 collaboration core uplifted to High), Group 9, Artificial Intelligence (AI) L2 (11 forks, the platform layer around models), Group 8, Cybersecurity & Risk Management L3-adjacent (16 forks, the defensive substrate at High), Group 10, Collaboration L1 (10 forks, the lightest tier), Group 11, Communication L2 (10 forks, the messaging substrate), Group 13, Education & Training L2 (8 forks, the learning records substrate), Group 12, Data Management L2 (8 forks, the data governance substrate), Group 15, Contact Center L2 (5 forks, the case-records substrate), Group 14, Communication L3-adjacent (6 forks, the messaging substrate at High), Group 16, Cybersecurity & Risk Management L1 (5 forks, the defensive substrate at the lightest tier), Group 17, Development Tools L1 (5 forks, the development-lifecycle records substrate), Group 18, Health & Wellness L2 (5 forks, the wellness records substrate), Group 20, Content Management System (CMS) L2 (4 forks, the content registry substrate), Group 19, Construction L2 (4 forks, the project-records substrate), Group 21, Human Resources L2 (4 forks, the HR records substrate), Group 22, Artificial Intelligence (AI) L3-adjacent (3 forks, the platform layer at High), Group 24, Content Management System (CMS) L1 (2 forks, the lightest tier), Group 23, Accounting L3-adjacent (2 forks, the ledger at High), Group 26, Customer Service L1 (2 forks, the incident-records substrate), Group 25, Customer Relations Management (CRM) L2 (2 forks, the service-records substrate), Group 27, Customer Service L2 (2 forks, the category complete at both tiers), Group 28, Data Management L3-adjacent (2 forks, the governance substrate at High), Group 29, Development Tools L2 (2 forks, the category complete at both tiers), and Group 30, Education & Training L1 (2 forks, the category complete at both tiers), are spec'd (one sheet per fork, every claim evidenced), merged under the Merge Rule, and their common cores are built and tested in groups/analytics-l2/ (136 tests), groups/collaboration-l2/ (192 tests), groups/analytics-l3/ (183 tests), groups/cybersecurity-l2/ (194 tests), and groups/accounting-l2/ (219 tests), groups/analytics-l1/ (136 tests), groups/collaboration-l3/ (239 tests), groups/ai-l2/ (146 tests), groups/cybersecurity-l3/ (236 tests), groups/collaboration-l1/ (192 tests), groups/communication-l2/ (82 tests), groups/education-training-l2/ (65 tests), groups/data-management-l2/ (196 tests), groups/contact-center-l2/ (107 tests), groups/communication-l3/ (138 tests), groups/cybersecurity-l1/ (194 tests), groups/development-tools-l1/ (66 tests), groups/health-wellness-l2/ (67 tests), groups/cms-l2/ (98 tests), groups/construction-l2/ (146 tests), groups/human-resources-l2/ (77 tests), groups/ai-l3/ (193 tests), groups/cms-l1/ (98 tests), groups/accounting-l3/ (273 tests), groups/customer-service-l1/ (69 tests), groups/crm-l2/ (96 tests), groups/customer-service-l2/ (69 tests), groups/data-management-l3/ (239 tests), groups/development-tools-l2/ (66 tests), and groups/education-training-l1/ (65 tests), each with mutation-verified negative controls. Fourteen extended functions from the group's union spec are specified but not yet implemented; they are listed in the group's UNION-SPEC.md. See CONCEPT.md for the design and PIPELINE.md for the build order.

## License

Apache-2.0. Copyright 2026 Aries Hilton.
