# Operation DeadRamp — concept (Aries, Oct 25, 2026)

His words: "It takes all the FedRamp vendors and open source reverse engineer their service and products into one collective repo! Like each FedRamp vendor is a fork for dead ramp." (Correction appended by him seconds later: "service and products.")

## The idea
FedRAMP-authorized vendors sell the government cloud services and products at premium prices behind a compliance gate. DeadRamp treats the FedRAMP Marketplace as a public index of what the government actually buys, models each vendor's service/product from its public surface (marketplace listing, public docs, APIs, standards), and clean-room builds an open-source equivalent for each — one collective repo, one fork/module per vendor.

## Architecture sketch
- Index: FedRAMP Marketplace listings (vendor, product, service category, authorization level) as the map.
- Spec: public documentation, public APIs, and the underlying open standards each product implements.
- Build: clean-room implementations (the Kindling doctrine: study how the incumbent solves the problem, implement the method, never copy proprietary code), each vendor = one fork/module under one collective repo.
- Compliance layer: the FedRAMP control baseline (NIST 800-53) is itself public — the controls map becomes shared infrastructure across all forks instead of a per-vendor toll.

## Lineage
Nation Kit modeled the federal AGENCIES as software. DeadRamp models the VENDOR LAYER underneath the agencies: the suppliers the agencies are forced to rent from. Same thesis as everything else he builds: if the gate is the business model, open source is the counter-move.

## Status
Concept captured Oct 25, 2026. First fork/category target is Aries's call.

## Phase 1 (Aries, Oct 25, 2026): MAP ALL THE FORKS
His ruling: "Hell we got to do them all" — the first task is not one fork, it is mapping ALL the forks to each other. And his matching key: use CMMC levels to match the forks of the FedRAMP vendors.

Map design:
- Axis 1 — FUNCTION (what the fork does): FedRAMP service category + service model (IaaS/PaaS/SaaS).
- Axis 2 — TRUST TIER (who may use it, at what assurance): CMMC level crosswalk.
  - FedRAMP baselines are tailored NIST SP 800-53 control sets (Low/Moderate/High).
  - CMMC 2.0: L1 = FCI (FAR 52.204-21 practices); L2 = CUI, the 110 practices of NIST SP 800-171 (which map onto 800-53 controls); L3 = 800-171 + a subset of NIST SP 800-172.
  - Crosswalk rule for the map: FedRAMP Low ≈ CMMC L1 tier; FedRAMP Moderate ≈ CMMC L2 tier (800-53 Moderate covers the 800-171 substrate); FedRAMP High ≈ CMMC L3-adjacent tier. This is a planning/matching equivalence, stated as such: FedRAMP authorizes PRODUCTS, CMMC certifies ORGANIZATIONS; the map matches forks by tier, it does not claim either credential.
- Sibling forks = same category + same CMMC tier (direct substitutes). Stack relations = IaaS forks under PaaS forks under SaaS forks.
- Deliverable: fork registry (every FedRAMP-authorized vendor/product), CMMC crosswalk table, relation map — in this workspace.

## Merge rule (Aries, Oct 25, 2026): merges are NIST compliant
How forks merge is governed by NIST, not taste:
- A merge takes the UNION of the parent forks' control baselines, never the intersection — merging can never dilute a control.
- The merged fork inherits the HIGHEST trust tier (CMMC crosswalk tier / FedRAMP impact level) of its parents, and must satisfy that tier in full.
- Every merge carries control traceability: which parent contributed which controls, so compliance is provable from the record.
- The merge process itself follows NIST secure-development practice (SP 800-218 SSDF): provenance, review, and verification before a merge lands.
