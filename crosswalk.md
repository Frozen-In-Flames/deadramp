# Operation DeadRamp — CMMC ↔ FedRAMP Crosswalk

The fork map's second axis. FedRAMP speaks in impact levels (Low / Moderate / High); CMMC speaks in levels (L1 / L2 / L3). This crosswalk is the matching key that lets forks from the two worlds be compared, grouped as siblings, and merged under one rule.

## The crosswalk

| FedRAMP impact level | Control baseline (what it is) | CMMC tier on the map | CMMC basis | Forks at this tier |
|---|---|---|---|---:|
| Low | Tailored NIST SP 800-53 Low baseline | **L1** | FCI safeguarding: the 17 practices of FAR 52.204-21 | 24 |
| LI-SaaS | Tailored subset of the 800-53 Low baseline, for SaaS offerings | **L1** | Same Low-baseline family as above | 42 |
| Moderate | Tailored NIST SP 800-53 Moderate baseline | **L2** | CUI safeguarding: the 110 practices of NIST SP 800-171 | 450 |
| High | Tailored NIST SP 800-53 High baseline | **L3-adjacent** | 800-171 plus a subset of NIST SP 800-172 enhanced requirements | 124 |
| Unknown (no baseline assigned in source) | — | *(none)* | Cannot be tiered until a baseline exists | 141 |

Tier labels are stored in `forks.json` exactly as **"L1"**, **"L2"**, **"L3-adjacent"** (and `null` where no tier can be assigned).

## Reasoning

- **The substrate is shared.** FedRAMP baselines are tailored selections from NIST SP 800-53. CMMC Level 2's 110 practices come from NIST SP 800-171, which is itself drawn from the 800-53 control families (800-171's requirements map onto 800-53 controls). The two regimes are different selections from the same control universe, which is what makes a tier match meaningful at all.
- **Low ↔ L1.** Both are the floor tier: FedRAMP Low protects low-impact data with a reduced 800-53 baseline; CMMC L1 protects Federal Contract Information with basic cyber hygiene (FAR 52.204-21). LI-SaaS rides along because it is FedRAMP's own tailoring of the Low baseline for SaaS.
- **Moderate ↔ L2.** FedRAMP Moderate is the workhorse tier for systems holding data whose loss would cause serious adverse effect; its 800-53 Moderate baseline covers the full 800-171 substrate that CMMC L2 certifies for Controlled Unclassified Information. Same weight class, same control depth.
- **High ↔ L3-adjacent.** FedRAMP High is the deepest 800-53 baseline. CMMC L3 adds selected NIST SP 800-172 enhanced requirements on top of the L2 substrate. "Adjacent" is deliberate wording: L3 is not identical to FedRAMP High, but it is the only CMMC tier in High's weight class, so High forks are matched to it for planning.
- **Unknown gets no tier.** 141 marketplace listings have no impact level assigned yet in the source (mostly pipeline offerings). Inventing a tier for them would corrupt every sibling group they touched, so they are left untiered until the source assigns a baseline.

## The caveat (read before using the map)

**FedRAMP authorizes products; CMMC certifies organizations.** A FedRAMP impact level is a statement about a cloud service offering and the data it may hold. A CMMC level is a statement about a company and how it handles FCI/CUI. The crosswalk above is a **planning and matching equivalence for the DeadRamp map only**: it says "these forks sit at comparable assurance weight," so they can be grouped as siblings and merged consistently. It does **not** claim that a FedRAMP-authorized product confers CMMC certification on anyone, that a CMMC-certified organization holds a FedRAMP authorization, or that either regime accepts the other as evidence. Any real compliance claim still has to be earned inside each regime separately.

## Merge Governance (the Merge Rule)

How forks merge is governed by NIST, not taste. These rules bind every merge in Operation DeadRamp:

1. **Union, never intersection.** A merge takes the **union** of the parent forks' control baselines. Every control either parent carried survives the merge. Merging can never dilute a control; a merge that would drop a control is not a merge, it is a downgrade, and it is prohibited.
2. **Highest tier wins.** The merged fork inherits the **highest** trust tier of its parents — both the FedRAMP impact level and the CMMC crosswalk tier (e.g., merging an L1 fork with an L2 fork produces an L2 fork) — and must satisfy that tier **in full**, not approximately and not eventually.
3. **Control traceability.** Every merge carries a traceability record: which parent contributed which controls. Compliance of the merged fork must be provable from the record — a reviewer must be able to walk from any control in the merged baseline back to the parent fork (and from there to the parent marketplace listing) that contributed it.
4. **SSDF process.** The merge process itself follows NIST SP 800-218 (Secure Software Development Framework) practices: **provenance** (the merged fork's lineage and inputs are recorded), **review** (the merge is examined before it lands, not after), and **verification** (the merged fork is tested against its inherited tier's requirements before it is treated as satisfying them).

Sibling groups in `MAP.md` (same category, same tier) are the standing merge candidates: they are the forks whose union can be taken without changing tier. Cross-tier merges are permitted by these rules but always resolve upward, per rule 2.
