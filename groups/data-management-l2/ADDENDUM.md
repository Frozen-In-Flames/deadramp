# Addendum — Data Management, CMMC L2: the 5 remainder additions

This addendum extends [`UNION-SPEC.md`](UNION-SPEC.md) with the 5
previously uncategorized forks of remainder build unit
**`addition:data-management-l2`** (see `../../REMAINDER.md`). The
original union spec stands as written: its taxonomy, its 12-function
core, its control baseline, and its Extended dispositions are
**unchanged**. This document records what joined, what the newcomers
claim under the group's existing taxonomy, the core-delta decision
for every claimed function, and the updated union statement.

**Headline: forks spec'd 5 / 5; 6 new claims; core delta — zero
functions extended, `src/` byte-identical; tests 196 → 208, all
passing; no new gap functions** (four already-registered Extended
gaps gain claimants, listed in §5, and the file-transfer transport
gap gains a zero-claim described-function member, recorded with its
caveat).

## 1. Membership and method

The 5 forks, in unit order (FedRAMP ID — vendor / product):

| # | Fork | Vendor / product |
|---|---|---|
| 1 | `FR1706403967` | Collibra / Collibra Platform for Government (CPG) |
| 2 | `FR1814557199` | DNAnexus, Inc. / DNAnexus Platform |
| 3 | `FR2029331613` | Informatica LLC / Informatica Intelligent Cloud Services (IICS) |
| 4 | `FR1901136437` | Synergetics Incorporated / Open Federal Logistics Information System (OpenFLIS) |
| 5 | `FR2025456731` | Vaultara, LLC / Vaultara Flare Services |

Method, identical to the original pass:

- Spec sheets were produced by `scratch/additions_extract.py`,
  which **parses the taxonomy out of the group's original
  `scratch/extract.py`** rather than re-typing it — the 19 families
  (id, label, regex) are the shipped ones by construction, applied
  verbatim, not re-tuned for the newcomers. Same sentence splitting,
  same evidence rule (first matching sentence, truncated at 400
  chars), same sheet schema. The 5 sheets are **appended** to
  `specs/specs.json` after the original 8, which are byte-for-byte
  untouched (verified by deep-equality against the git HEAD parse
  and by identical re-serialization of the original prefix; see
  `scratch/append_additions.py`).
- Sources are the same cached GSA FedRAMP Marketplace dataset
  (`../../raw/data_dump.json`), joined by FedRAMP ID. All 5
  descriptions were present; no live fetching. All 5 are FedRAMP
  **Moderate**, so the group stays single-tier and the L2 baseline
  is inherited in full (Merge Rules 1–2), unchanged.
- The census starting point was verified, not trusted: all **7
  census citations** for these forks were re-checked against the
  forks' own cached descriptions and **7 / 7 verify** as verbatim
  substrings under whitespace normalization (the raw dump wraps
  lines mid-sentence). Recorded in
  `scratch/additions_citation_check.json`. Verification of a
  citation is verification that the census quoted the description
  honestly — it does **not** make the cited sentence a claim.
  Three of the 7 citations tag no family at all (see §2): the
  census chose them to justify the category, and under this
  group's taxonomy they earn nothing.

## 2. What the additions claim

**6 claims** across the 5 forks; 4 of 5 carry at least one claim.
Claim counts per family among the additions, with the group's
combined count (original 8 + additions = 13 forks) alongside:

| Function | Additions claiming | Group total (13) | Disposition (UNION-SPEC) |
|---|---:|---:|---|
| Integration, connectivity & data exchange | 2 | 6 | Core substrate; runtimes Extended |
| Catalog search & discovery | 1 | 3 | **Core** — metadata search; indexing Extended |
| Query, reporting & analytics | 1 | 3 | Core substrate; engines Extended |
| Workflow, automation, review & approvals | 1 | 3 | Extended — engines; approval substrate Core |
| Data governance & access controls | 1 | 2 | **Core** — access governance |

Per-fork claim counts: Informatica IICS **3** (`integration_exchange`,
`data_governance`, `query_reporting`), Collibra CPG **1**
(`workflow_automation`), DNAnexus **1** (`integration_exchange`),
OpenFLIS **1** (`catalog_search`), and **zero** for Vaultara Flare
Services. The full per-fork table is pinned literally in
`tests/test_additions.py` (`EXPECTED_CLAIMS`).

### Zero-claim fork — pinned, not hidden

One addition carries **zero claims**, for the same reason Login.gov
carries none in the Cybersecurity L2 additions: its own marketplace
description phrases its function in none of the taxonomy's 19
patterns, and the taxonomy was not re-tuned to catch it.

- **Vaultara Flare Services** (`FR2025456731`) — a secure file
  transfer product whose description says "secure, bi-directional
  electronic transfer to any digital file" and "secure digital
  delivery of data". The group's `file_transfer` family keys on
  "managed file transfer" / "MFT" (the phrasing of Sharetru, inside
  the GovPoint bundle) — Vaultara uses neither phrase, and no other
  pattern fires on its text. Both of its census citations verify
  as description text and tag nothing. Its substrate case is
  nevertheless exercised in the tests (ingestion records with a
  checksum, export manifests over supplied records — the
  transfer-shaped records the build does hold), with the zero-claim
  status stated in the test's own docstring.

### Near-misses, itemized per fork

Sentences that carry family-adjacent substance but match no pattern
(the full feed is `scratch/additions_near_miss_feed.json`):

- **Collibra CPG** — "your system of record for data" (its census
  citation) is not `dataset_registry`: the family keys on
  dataset/registry/repository/records-management phrasing, and
  "system of record" is none of them. "integrated Data Intelligence
  platform" is not `integration_exchange` (the pattern requires
  "integrated into"; bare "integrated" does not fire). "connects IT
  and the business" is not the family's "connecting"/"connect data"
  either. "automate processes, manage compliance" earns no second
  claim: no "workflow" follows "automate", and "manage compliance"
  is not `data_governance` phrasing.
- **DNAnexus** — Its census citation, the long platform sentence
  ("analysis and data management platform … to discover
  relationships …"), tags nothing: "analysis" is not the
  `query_reporting` family's "analytics", "discover relationships"
  is not "cohort discovery" / "discover shared|cohorts", and
  "research communities" does not tag `catalog_search` (the word
  boundary in `\bsearch\b` is exactly what keeps "research" from
  firing). The `integration_exchange` claim rests on the second
  paragraph's "an API for integration with upstream and downstream
  systems" — which does **not** earn `api_access` (that family keys
  on "via our api" / "via the api" / "programmatic access").
  "Electronic Data Capture" is not `ingestion_collection` phrasing
  and "Laboratory Information Management" is not "records and
  information management" for `dataset_registry`.
- **Informatica IICS** — "industry-leading metadata capabilities"
  tags nothing (the taxonomy has no metadata family; `dataset_registry`
  does not key on metadata, and this build's registry is of datasets,
  not metadata). "data set" (spaced, in the CAI sentence) is not
  `dataset` for `dataset_registry`. "automate business processes"
  and "process orchestration" are not `workflow_automation` (no
  workflow noun follows "automate"; orchestration has no family
  here). The `query_reporting` claim rests on "enable real-time
  analytics"; the `integration_exchange` evidence sentence is the
  description's Cloud Data Integration block, which the group's
  sentence splitter keeps as one sentence through its section
  header — the same splitting the original 8 were tagged under.
- **OpenFLIS** — "data collation, retrieval, and dissemination" is
  the census's category evidence and the `catalog_search` claim
  rests on its "search and display information across multiple
  databases"; but "collation" is not `ingestion_collection`
  ("data collection" is the pattern) and dissemination tags no
  export/integration family. In the module-list sentence,
  "provisioning, cataloging" is not `asset_lifecycle` (that family
  keys on "provisioning of … clusters" / Kubernetes phrasing), and
  "Information Management / Knowledge Management (IM/KM)" is not
  "records and information management" for `dataset_registry`.
- **Vaultara Flare** — see the zero-claim entry above; all three of
  its watch-listed sentences (transfer, sharing, delivery) match no
  pattern.

## 3. Core-delta decisions

Every family the additions claim already has a disposition in
UNION-SPEC, and every Core family's records form already exists in
the build. The per-family decision:

| Claimed family (additions) | Disposition | Core delta |
|---|---|---|
| Integration, connectivity & data exchange (2) | Core 1/3/4/9 substrate — sources, ingestion, export, API; connector/runtime engines Extended | **Carried** — no change; runtime gap gains 2 claimants |
| Data governance & access controls (1) | Core 7 — access requests, decisions, grants | **Carried** — IICS's "data governance functions" land in the same purpose-bound request/decision/grant records Datavant's claim presupposed |
| Catalog search & discovery (1) | Core 2 — literal metadata search; indexing engines Extended | **Carried**; indexing gap gains 1 claimant |
| Query, reporting & analytics (1) | Core 5/9 substrate — provenance and export records; query/visualization engines Extended | **Carried**; engine gap gains 1 claimant |
| Workflow, automation, review & approvals (1) | Extended — workflow/BPM engines; the approval substrate is Core 7 | **Carried** — Collibra's "automate data workflows" is engine substance; nothing it presupposes is missing from the substrate. Gap gains 1 claimant |
| Managed file transfer (0 claims) | Extended — transport | **No delta** — Vaultara claims nothing; see §5 for how its membership in the gap is recorded |

**Result: the core is unchanged.** No function the 5 claim
presupposes a records form the build lacks: IICS's governance is
the access-governance flow, DNAnexus's and IICS's integration is
the source/ingestion/export substrate, OpenFLIS's discovery is the
catalog search, and Collibra's workflow claim's Core side is the
approval substrate. `src/` is byte-identical to the shipped build
(`src/datamgmt/store.py` SHA-256
`dc35677ccdaf4d416a10a5364128f54bb1b1802fd8a99c00271ad081caf2774e`
before and after this addendum's work, the mutation drill
included — the same hash recorded at the original ship in
`scratch/store.py.sha256`). The tier baseline does not change:
same tier by construction.

## 4. Updated union statement

The group now covers **13 forks** (8 original siblings + 5
remainder additions), **34 claims** in total (28 + 6), with
**12 of 13** forks carrying at least one claim. The merged build
remains the same 12-function governance substrate — dataset
registry with versioned schemas, catalog search, source registry,
ingestion records, provenance, deterministic quality rules and
check runs, access governance, retention schedules, export
manifests, API, RBAC, audit log — now spec'd against 13
marketplace offerings instead of 8. The additions reinforce the
original spec's central finding rather than shifting it: this
category's shared surface is governance over data, and the
newcomers' engines on top of it (integration runtimes,
data-intelligence platforms, bioinformatics analysis, discovery
indexes, transfer transports) stay Extended, exactly as the
original 8's engines did.

## 5. Gaps — for the registry at ship

**No new gap functions.** Every Extended family the additions
claim was already specified and registered for this group; the
additions raise claimant counts on existing gaps. For `GAPS.md`,
the existing entries gain these claimants:

- **Integration runtime & connector engine** — +2: DNAnexus
  Platform, Informatica IICS (live connectors, transformation
  execution, automation runtime)
- **Workflow / BPM execution engine and guided-interview engine**
  — +1: Collibra CPG (its "automate data workflows" is the engine
  side of the family's claim; the approval substrate stays Core)
- **Enterprise search indexing engine** — +1: OpenFLIS (discovery
  across multiple databases at scale; the core's search is over
  registry metadata)
- **Query & visualization engines** — +1: Informatica IICS
  (real-time analytics delivery; the core holds the records and
  provenance such engines would render)
- **Managed file transfer transport** — Vaultara Flare Services
  joins as a **described-function member with zero taxonomy
  claims**: its description's transfer/delivery function is the
  transport this gap names, and the census routed it to this
  group on that basis, but it earned no `file_transfer` claim
  under the verbatim taxonomy (see §2). Recorded here so the
  final batch's worklist for this gap includes the offering
  without overstating its claim status.

Domain engines the newcomers operate that earned no family claim
are **not** registered as gaps — they are recorded as near-miss
substance in §2 (DNAnexus's molecular-analysis platform,
Collibra's data-intelligence catalog platform), the same
discipline the original pass applied to unclaimed substance.

## 6. Verification

- Spec integrity is pinned by tests: sheet count and order,
  membership against `remainder.json`, the literal per-fork claim
  table, the zero-claim set, verbatim evidence, and the
  single-tier invariant (see `tests/test_additions.py`).
- Every addition fork is exercised against the substrate in the
  same tests: the access-governance flow (including the
  self-decision denial) for Collibra, sources/ingestion/provenance
  for DNAnexus, governance + search + a deterministic quality
  check for IICS, catalog search for OpenFLIS, and
  ingestion + export-manifest checksum records for Vaultara.
- **Tests: 196 → 208, all passing** (12 tests in the additions
  module: 7 spec-integrity, 5 per-fork substrate cases).
- **Negative control:** the core is unchanged, so the group's
  signature drill was re-run in this tree: `_check_decider_not_requester`
  in `src/datamgmt/store.py` was patched to a no-op and the full
  suite ran — **208 tests, exactly 5 failures**: the shipped
  drill's 4 (two in `test_access_governance`, two in
  `test_negative_control`) plus the additions module's Collibra
  case, whose guard-isolated self-decision leg (a name-identical
  decider holding `access_decide`, the isolation
  `test_negative_control.py` documents) trips on the mutant as
  designed. `store.py` was restored from the pre-mutation copy
  and verified SHA-256-identical to the shipped hash; the suite
  re-ran green. Recorded in `tests/README.md`; raw record in
  `scratch/additions_mutation_run.txt`. (Transparency note in
  that record: a first drill run failed only the original 4,
  because the additions case's plain-viewer leg is also denied
  by the permission layer; the case was strengthened to isolate
  the guard, the suite re-verified green, and the drill re-run —
  the 5-failure run is the recorded one.)
