# Union Spec — Data Management, untiered set (DeadRamp Phase 2, remainder)

The union contract for the **untiered set** of Data Management:
**8 forks**, **tier null**. Every member's FedRAMP impact level is
**Unknown** in the source dataset — the source publishes no baseline
for these offerings — so no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented control
claims; tier stays null in the registry until the source publishes a
baseline." The Documented control claims section below replaces the
baseline section a tiered group's union spec carries.

Membership is exactly census unit `untiered:Data Management` in
`../../remainder.json` (8 fork IDs, verified mechanically). In
`forks.json` the set is mixed as filed: 4 forks carry the Data
Management category, 2 are filed under Artificial Intelligence (AI),
1 under Analytics, and 1 as "Uncategorized (none in source)"; the
census assigned all 8 to Data Management from their own
descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span FedRAMP Certified (2),
Initial Implementation (5), and Legacy FedRAMP Ready (1) — a status
is record data, not a claim. Service models: SaaS (7), PaaS (1).

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 8
entries, each with the offering's full public marketplace
description and its function claims tagged from that description,
every claim carrying the source sentence as evidence, every sheet
recording `fedramp_impact_level: "Unknown"` and `cmmc_tier: null`.
Sources: GSA FedRAMP Marketplace dataset (cached at
`../../raw/data_dump.json`, produced by the General Services
Administration, last change 2026-10-22), product records joined by
FedRAMP ID. All 8 descriptions were present in the cached dataset
and match `../../remainder/uncovered.json` exactly (8/8).

## How functions were counted

The category's fixed 19-function taxonomy was applied **verbatim**:
the extractor in `scratch/extract.py` AST-parses the TAXONOMY
literal out of the founding group's extractor
(`../../data-management-l2/scratch/extract.py`, parsed, never
executed) and asserts it is the same 19 families before tagging.
Taxonomy-verbatim proof: before tagging this set, the extractor
reproduced the founding group's **original shipped claim tables
exactly — 8 of 8 forks, 28 of 28 claims, deep-equal** against the
sheets at the original ship commit (f90acfb) — using the parent's
sentence split (carriage returns replaced with a space before
splitting, the founding group's documented normalization) and
evidence rule (first matching sentence; over 400 characters,
truncated to 397 + '...').

The founding group's six recorded wording-artifact corrections are
embodied in the taxonomy patterns themselves (implementation
substrate earns nothing — there is no bare "storage" / "database" /
"identity" family; "lifecycle" splits by phrase; there is
deliberately NO audit family — vendor-operational logging of an
offering is not a customer-facing audit function;
workflow_automation requires automation-platform /
automate-a-workflow phrasing; data_governance keys on "data
governance" / "governance controls" only; claims come from
description text only, never from business_categories). An
exclusion pass scanned every raw hit's evidence sentence for
third-party hosted-app catalogue segments and scope-exclusion
sentences: **no hits were removed** — no description in this set
contains a third-party hosted-app catalogue segment, and no
evidence sentence carries scope-exclusion phrasing. The set's one
scope passage (OcientAIQ's FedRAMP-scope paragraph, placing
customer-operated deployments outside the cloud offering) fires no
family and is recorded in `scratch/ARTIFACTS.md`. First-party
component/functionality catalogues (ZL Unified Archive's "Key
functionalities" list) stand at catalogue weight, per the founding
group's GovPoint posture; adjudications and wording artifacts are
itemized in `scratch/ARTIFACTS.md`.

A function is claimed for a fork **only** when its own description
contains matching text; counts are a **floor**, not a ceiling.
**13 claims** across the set; **6 of 8 forks carry at least one
claim**. The two zero-claim forks are recorded under Named
absences, not hidden.

Census citations: 11 citations are recorded for these forks in the
census; **11 of 11 verify** as verbatim substrings of the forks'
own descriptions (whitespace-normalized), and **6 of 11** are
themselves a claim evidence sentence. Verification is not a claim,
in either direction; the per-citation record is
`scratch/citation_check.json`.

## Function ranking — all 8 set members

Dispositions are the category's standing disposition per family,
taken from the founding group's union spec unchanged.

| # | Function | Forks claiming (of 8) | Disposition in this build |
|---|---|---:|---|
| 1 | AI/ML analysis & orchestration | 6 | Extended (models and AI engines; the build ships no model) |
| 2 | Catalog search & discovery | 2 | **Core** (metadata search; indexing engines Extended) |
| 2 | Ingestion & data collection | 2 | **Core** (ingestion records; collection engines Extended) |
| 4 | Dataset, records & repository registry | 1 | **Core** (dataset registry) |
| 4 | Retention, disposition & records lifecycle | 1 | **Core** (schedules + due evaluation; disposition execution Extended) |
| 4 | Query, reporting & analytics | 1 | Core substrate (records/provenance); query/visualization engines Extended |
| 7 | Integration, connectivity & data exchange | 0 | Core substrate (sources, ingestion, export, API); connector/runtime engines Extended — **zero claimants in this set; named absence** |
| 7 | Record linkage & matching | 0 | Extended (linkage engines) — zero claimants in this set |
| 7 | Data governance & access controls | 0 | **Core** (access governance) — **zero claimants in this set; named absence** |
| 7 | Privacy preservation & de-identification | 0 | Extended (de-identification engines) — zero claimants in this set |
| 7 | Content processing (OCR, transcription, categorization) | 0 | Extended (processing engines) — **zero claimants in this set; named absence** |
| 7 | Data quality, accuracy & completeness validation | 0 | **Core** (quality rules + check runs) — **zero claimants in this set; named absence** |
| 7 | Workflow, automation, review & approvals | 0 | Extended (engines; the approval substrate is Core) — zero claimants in this set |
| 7 | Guided data collection (forms & intelligent interviews) | 0 | Extended (interview engine) — zero claimants in this set |
| 7 | API / programmatic access | 0 | **Core** (REST API) — **zero claimants in this set; named absence** |
| 7 | Asset, cluster & infrastructure lifecycle management | 0 | Extended — zero claimants in this set |
| 7 | Cloud platform hosting (compute, storage, private cloud) | 0 | Extended (IaaS/PaaS) — zero claimants in this set |
| 7 | Case management & adjudication | 0 | Extended — zero claimants in this set |
| 7 | Managed file transfer | 0 | Extended (transport) — **zero claimants in this set; named absence** |

This set is heterogeneous in a different way from the founding
group: six of its eight forks are AI-adjacent offerings the census
assigned to Data Management (two are filed under AI outright), and
ai_ml is its dominant family (6 of 8), while the governance
families the founding group was built on are thin or absent here.
The counts say so plainly rather than smoothing it over.

## The Core — what this build implements (12 functions)

**Core-boundary decision (stated once):** the build carries the
founding group's twelve-function substrate **whole** — dataset
registry with versioned schemas; catalog search; source registry;
ingestion records; provenance view; data quality rules and check
runs; access governance (purpose-bound requests, decisions never by
the requester, time-boxed grants); retention schedules with due
evaluation; export manifests; REST API; RBAC; append-only audit
log. The substrate is records machinery: every dataset, source,
ingestion, and export is a **metadata record carrying pointers and
checksums only — never content** — and it is tier-independent code:
the founding source contains no tier or baseline machinery, so
there was nothing tier-shaped to strip. Where the founding
contract's text ties functions to the Moderate/L2 baseline, read it
here as **baseline-neutral substrate**, claimed against no
baseline.

Claim support in THIS set, stated honestly per function:

- **Claim-supported by a taxonomy family here (4 of 12):** dataset
  registry (by `dataset_registry`, ZL Unified Archive); catalog
  search (by `catalog_search`, Pinecone and ZL Unified Archive);
  ingestion records (by `ingestion_collection`, Ardoq and
  OcientAIQ); retention schedules (by `retention_disposition`, ZL
  Unified Archive).
- **Carried, not claimed in this set (8 of 12):** source registry
  and provenance view (substrate of ingestion; no family of their
  own, exactly as in the founding build); data quality
  (`quality_validation` has 0 claimants here); access governance
  (`data_governance` has 0 claimants here — see Named absences);
  export manifests (no export family exists; `integration_exchange`
  has 0 claimants here); REST API (`api_access` has 0 claimants
  here, despite API prose in four descriptions); RBAC and audit log
  (substrate hooks; this taxonomy has no audit family, by the
  founding group's deliberate design).

The carried code is **byte-identical** to the founding group's
`src/datamgmt/` (7 modules; SHA-256 accounting in this group's
README and `tests/README.md`). The implementation contract is the
founding spec's contract, unchanged: Python 3, standard library
only, package `datamgmt` under `src/`, ids sequential per object
type with fixed prefixes (`ds-`, `src-`, `ing-`, `qr-`, `qc-`,
`ar-`, `gr-`, `rp-`, `ex-`), failed operations consume no id and
change nothing, permission checks precede mutation, all timestamps
UTC ISO-8601, roles `admin|steward|viewer` with the founding
permission matrix, retention due state and export checksums derived
from recorded facts, and the audit log append-only with denied
attempts recorded.
...[truncated 10368 chars]
## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 8 offerings (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own marketplace
descriptions assert, in their own words. A documented control claim
is a **fork's claim about itself**, recorded here with its
evidence; it is not the build's control attainment, and nothing in
this section fills a family in from any baseline.

Two layers, kept distinct. The taxonomy layer records control
language that fired a taxonomy family. The prose tier records
control language asserted outright in a fork's sentences that fires
no family — documented here (the Untiered Set 2 precedent) so the
set's control posture is visible without converting prose into
taxonomy claims it did not earn.

Documented via a taxonomy family:

- **Information management & retention (SI-12)** — via
  `retention_disposition`, **1 fork**: ZL Unified Archive
  (FR2504771625 — "records capture, storage, retention, and
  disposition for all federal agencies", tailored to the Federal
  Records Act and the National Archives and Records Administration
  (NARA) requirements it names).

Documented at the prose tier (control language in the forks' own
sentences; no taxonomy family fired):

- **Access control (AC)** — Immuta (FR2629068833 —
  "attribute-based access and control (ABAC) of data"; "Immuta
  enforces their access based on the defined policies"; temporary,
  scoped roles for AI agents, "automatically removed once the task
  is complete, so no standing privilege persists"); ZL Unified
  Archive (FR2504771625 — "Access to all data is restricted to
  authorized personnel of each agency").
- **Identification & authentication (IA)** — Immuta (FR2629068833 —
  "Authentication to Immuta's service is controlled via a variety
  of Single Sign-on (SSO) and directory systems"); ZL Unified
  Archive (FR2504771625 — exports "necessitate authentication
  through an identity management system approved by each agency").
- **Audit (AU)** — Immuta (FR2629068833 — "robust auditing of
  actions taken within the platform"; a "dual-identity audit trail"
  for agent activity); ZL Unified Archive (FR2504771625 — "A
  complete audit log details all actions taken on documents").
  Recorded as the forks' claims: this taxonomy has no audit family
  (the founding group considered and rejected one), so no audit
  *function* is claimed for any fork, and the build's own audit log
  is substrate, claimed against no baseline.
- **Cryptographic protection (SC)** — Pinecone (FR2634450946 —
  "customer data encrypted at rest (AES-256, with a distinct data
  encryption key for every stored object...) and in transit (TLS
  1.2 minimum)"); ZL Unified Archive (FR2504771625 — "Data is
  stored in an encrypted content and data storage system"). The
  build performs no cryptography of its own; these are the forks'
  claims about themselves.

Control areas **not documented** by any fork in this set: every
other NIST SP 800-53 control family — including AT, CA, CM, CP,
IR, MA, MP, PE, PL, PM, PS, RA, and SA, and SI beyond the retention
sentence above — is asserted by no description in the set. If the
source later publishes an impact level for any of these offerings,
the tier is recorded then and not before.

## Named absences

- **Data governance & access controls — 0 of 8.** The headline
  absence: Immuta is a data-governance product whose description
  never uses the family's phrases ("data governance" / "governance
  controls") — it says "govern and provision data access" and "for
  governance purposes". Its governance substance is documented at
  the prose tier above; the claim is absent, not repaired, and the
  taxonomy was not re-tuned.
- **API / programmatic access — 0 of 8.** Four descriptions carry
  API prose (Files.com's "application and API", Immuta's
  "Application Programming Interface (API)", Pinecone's "documented
  APIs and client SDKs", ZL's "APIs enable the retrieval"); none
  uses the family's phrasing ("via our api" / "via the api" /
  "programmatic access").
- **Content processing — 0 of 8.** Wisedocs spells out "optical
  character recognition"; the family keys on the acronym "OCR"
  (and "transcription" / "categorize"), so the set's one document
  processing platform earns no content-processing claim.
- **Data quality validation — 0 of 8.** No description asserts
  accuracy/completeness validation in the family's phrasing; Core
  function 6 has no claimant in this set.
- **Integration & exchange — 0 of 8; managed file transfer — 0 of
  8.** Files.com's transfer function and the set's integration
  substance are described in prose that matches no pattern.
- **Zero-claim forks:** FR2630354495, Files.com (its whole
  description is one sentence; "transfer files" is not "managed
  file transfer", the Vaultara posture from the founding group's
  additions) and FR2629068832, OATI Marketplace ("warehousing, and
  retrieval" matches no family; its source business categories list
  AI, which earns nothing — claims come from description text
  only). The zeros are recorded, not repaired.

## Gaps (registered for the final batch)

Extended functions specified in this union spec, not implemented —
the founding group's engine gaps, restated here only where this
set's forks claim or describe them (counts are this set's), plus
the standing gaps this set does not touch:

- [ ] AI/ML analysis & orchestration engines (6 claimants — Ardoq,
  Immuta's agent governance, OcientAIQ, Pinecone, Wisedocs, ZL;
  the build ships no model)
- [ ] Vector database & embedding index engine (Pinecone — the
  build's search is literal substring over registry metadata, not
  vector similarity retrieval)
- [ ] Document processing engines: OCR, classification, duplicate
  detection (Wisedocs — described-function member; it earned no
  content_processing claim, see Named absences)
- [ ] Petabyte-scale data warehouse & analytics engine (OcientAIQ;
  OATI's warehousing described with no claim)
- [ ] Enterprise architecture graph-model platform (Ardoq)
- [ ] Policy enforcement plane & ABAC engine inside customer data
  platforms (Immuta — described with no data_governance claim; the
  build's access governance is records: requests, decisions,
  grants — not warehouse-side enforcement)
- [ ] Managed file transfer transport (Files.com —
  described-function member with zero claims)
- [ ] Archive, eDiscovery & FOIA production platform, including
  retention disposition execution and defensible deletion (ZL
  Unified Archive — the records substrate is Core; production and
  execution are Extended)
- [ ] Enterprise search indexing engine (2 claimants; the core's
  search is over registry metadata)
- [ ] Query & visualization engines (1 claimant)
- Standing category gaps with no claimant in this set, carried from
  the founding spec unchanged: integration runtime & connector
  engine; privacy-preserving record-linkage engine and
  de-identification engines (Immuta's Privacy Enhancing
  Technologies prose is adjacent substance, no claim); workflow /
  BPM execution engine and guided-interview engine; IaaS/PaaS
  hosting; case management depth; asset & cluster lifecycle
  engines; field-level / transformation lineage beyond ingestion
  records (claimed by no sibling in any Data Management set).
- Platform layer (gap-listed, never implied closed): encryption at
  rest (deployment layer — Pinecone and ZL document it for
  themselves; the build claims none); TLS only when a certificate
  is configured; multi-tenancy (the build is a single-tenant
  reference deployment); demo identities are hooks, not an IdP —
  IA-2 stays with the embedding organization.

## Coverage statement (for this build)

- Forks spec'd: **8 / 8** in census unit `untiered:Data
  Management`, each sheet recording the offering's own description
  and evidenced claims (13 total; 6 of 8 forks claiming at least
  one, 2 zero-claim forks recorded by name).
- Core implemented: **12 / 12** functions, carried byte-identical
  from the founding build.
- Tests: **202 tests run, 202 passed** (the founding group's
  196-test core suite carried with the code, plus 6 spec tests
  pinning this set), including the mutation-verified negative
  control (see `tests/README.md`).
- Tier: **null** on every sheet, pinned by tests. Nothing in this
  build claims a FedRAMP authorization, a CMMC certification, or a
  control baseline for any fork or for the build itself.
