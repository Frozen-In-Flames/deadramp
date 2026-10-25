# Union Spec — Data Management, CMMC L1 (DeadRamp Phase 2, Group 38 — singleton)

The functional spec for the Data Management **singleton** at the L1
tier: **1 fork**, per the singleton pipeline (PIPELINE.md: same
pipeline, group size one).

The fork: **Pagefreezer Website Archiving** (Pagefreezer Software
Inc., FR2409367364) — FedRAMP **LI-SaaS**, FedRAMP Certified, SaaS,
Public Cloud. Its actual impact level is recorded in its spec sheet
(`specs/specs.json`); LI-SaaS is FedRAMP's tailored subset of the Low
baseline for SaaS offerings, so this group's union baseline is the
Low baseline itself (see baseline section).

Reconciliation: the member set was verified three ways with
`scratch/verify.py` — **zero diffs**. (a) `specs/specs.json` set ==
`forks.json` select (category "Data Management", tier "L1") ==
{Pagefreezer Website Archiving}. (b) MAP.md reconciliation: MAP.md's
"Sibling groups" section lists only groups of size ≥ 2, so a
singleton has no prose section there; the MAP-side check is the
category arithmetic — MAP.md's Categories table gives Data
Management = 16 offerings, and `forks.json` splits them L2 8 +
L3-adjacent 2 + L1 1 + untiered 5 = 16, with MAP.md's L2 (8) and
L3-adjacent (2) sections present at exactly those counts. (c) The
fork's recorded impact level is LI-SaaS, matching the source record.

## How functions were counted

Group 12's 19-family taxonomy (Data Management L2) was applied
**verbatim** — same ids, labels, and matchers, including Group 12's
six wording-artifact corrections, which are part of the taxonomy's
calibration — so counts are comparable across the category's tiers
and nothing was re-tuned to fit this one fork. A family is claimed
only when the fork's own public description contains matching text;
the matching sentence would be stored as evidence in
`specs/specs.json`.

**Result: 0 claims.** The fork's entire public description is three
sentences of boundary prose (crawling technology, snapshots,
automated/scalable process, dynamic monitoring, always captured, up
to date), and no family's pattern fires on any of them. The full
near-miss record — archiving vs. `retention_disposition`, captured
vs. `ingestion_collection`, monitoring vs. the deliberately rejected
monitoring family, automated vs. `workflow_automation`, scalable
process vs. `platform_hosting`, the website archive vs.
`dataset_registry` — is in `scratch/ARTIFACTS.md`. Zero is reported
as the floor it is: the taxonomy was not loosened to manufacture a
claim for a singleton, and no function was invented for this fork.
(Precedent inside this category: several L2 descriptions are a
single marketing sentence; the floor is reported, not padded.)

## Function ranking — the 1 sibling

All 19 families sit at **0 of 1**. The ranking below is therefore by
disposition, not by claim count — there are no counts to rank. The
dispositions are the category's (Group 12's), restated for this
group: which families the carried substrate implements, which are
Extended engines, and which are absent from this group's union.

| Function family | Claims | Disposition in this build |
|---|---:|---|
| Dataset, records & repository registry | 0 | **Core** (carried substrate — see boundary decision) |
| Catalog search & discovery | 0 | **Core** (carried substrate; metadata search) — indexing engines Extended |
| Ingestion & data collection | 0 | **Core** (carried substrate: ingestion records) — the fork's capture engine Extended |
| Integration, connectivity & data exchange | 0 | **Core slice** (carried substrate: sources, export, API) — connector/runtime engines Extended |
| Data governance & access controls | 0 | **Core** (carried substrate: access governance) |
| Retention, disposition & records lifecycle | 0 | **Core** (carried substrate: schedules + due evaluation) — disposition execution Extended |
| Data quality, accuracy & completeness validation | 0 | **Core** (carried substrate: quality rules + check runs) |
| API / programmatic access | 0 | **Core** (carried substrate: REST API) |
| Workflow, automation, review & approvals | 0 | Extended — engines; the approval substrate is Core (access governance) |
| Query, reporting & analytics | 0 | Core slice (records/provenance substrate, carried) — query/visualization engines Extended |
| Record linkage & matching | 0 | Extended — PPRL engine (a category engine; no presence here) |
| Privacy preservation & de-identification | 0 | Extended — de-identification engines |
| Content processing (OCR, transcription, categorization) | 0 | Extended — processing engines |
| Guided data collection (forms & intelligent interviews) | 0 | Extended — interview engine |
| Asset, cluster & infrastructure lifecycle management | 0 | Extended — domain applications |
| Cloud platform hosting (compute, storage, private cloud) | 0 | Extended — IaaS/PaaS |
| Case management & adjudication | 0 | Extended — domain depth |
| Managed file transfer | 0 | Extended — transport |
| AI/ML analysis & orchestration | 0 | Extended — models |

Named absences, carried from Group 12 because they are properties of
the category taxonomy, not of any one group: **storage/database
engines are claimed as a customer-facing function by no Data
Management description at any tier built so far** — the build holds
metadata and records, not a database engine. **Field-level lineage
is claimed by no sibling either**; the build's provenance is at
ingestion granularity, and transformation lineage is an Extended
gap, recorded as such rather than implied.

## The core-boundary decision (read before the core)

This is the decision this singleton turns on, stated plainly:

- **No core function below is claim-supported for this fork.** The
  fork's description evidences zero functions under the verbatim
  taxonomy. Anyone who reads the coverage statement's "core
  implemented 12/12" as "the fork claims 12 functions" is being
  misled, so this section exists to prevent exactly that reading.
- **The category substrate is nevertheless carried in full at this
  tier.** The singleton method (per the build order) takes the core
  to be the category substrate the fork's claims presuppose; with
  zero claims, the presupposition is read at the level of the
  product's operation, and it is stated here as *interpretation, not
  evidence*: a website-archiving service holds a collection of
  captured records over time (→ dataset registry), takes them in
  through a capture process from registered sources (→ source
  registry, ingestion records, provenance), keeps them under
  retention expectations (→ retention schedules), lets authorized
  people find them and get them out (→ catalog search, export
  manifests, API), and must govern who may see and take what
  (→ access governance, RBAC, audit). Each step is a substrate
  function from Group 12's core; none of them is this product's
  engine.
- **The engines are not carried.** What makes this product an
  archiving product — the crawler, the page renderer, the change
  detector, the archive store and its replay — is Extended,
  named in the gaps. The substrate models an archive's governance;
  it does not capture a single web page, and this spec does not
  pretend otherwise.
- **The alternative was considered and rejected.** Building nothing
  because the description tags nothing would leave the category's
  L1 tier with no build while a tier-appropriate substrate exists
  and every other Data Management tier carries it. The price of
  carrying it is the disclosure above and in the coverage
  statement: **core carried, not claimed.** That price is paid in
  full, in both places.

## The Core — what the build implements (12 functions, carried)

Group 12's governance substrate, unchanged in behavior, claimed
against this tier's baseline:

1. **Dataset registry** — datasets (`ds-`) with owner, classification
   (public/internal/cui/phi), tags, and a **versioned schema** (field
   name, type, required, sensitive); schema updates increment
   `schema_version`.
2. **Catalog search** — literal, case-insensitive substring search
   across datasets (name, description, tags, schema field names),
   sources, and quality rules.
3. **Source registry** — data sources (`src-`) by kind
   (file/database/api/stream/manual) with location.
4. **Ingestion records** — ingestion runs (`ing-`) against a dataset
   from a registered source, with mode, record counts, checksum, and
   completed/failed status; every run is a recorded fact.
5. **Provenance view** — per dataset: the sources that have fed it,
   its ingestion runs, and total records over completed runs.
   Provenance at ingestion granularity, honestly bounded (see named
   absences).
6. **Data quality** — quality rules (`qr-`) of five kinds
   (completeness, uniqueness, format, range, freshness) and check
   runs (`qc-`) that evaluate a rule against a supplied batch of
   records with pinned, deterministic violation semantics.
7. **Access governance** — access requests (`ar-`) with a stated
   purpose and duration; decisions by a steward or admin who is
   **never the requester** (self-approval is denied at a single named
   seam and is the group's negative control); approvals mint
   time-boxed grants (`gr-`) that can be listed, filtered for
   actives, and revoked.
8. **Retention schedules** — one retention policy (`rp-`) per dataset
   (retention days, disposition delete/archive/review, legal hold)
   and a due evaluation that reports datasets past their retention
   window, referenced to their latest completed ingestion. The build
   schedules and reports; it does not execute disposition.
9. **Export manifests** — export records (`ex-`) with format, record
   count (supplied batch, or summed from completed ingestions), the
   dataset's schema version, and a SHA-256 checksum of the canonical
   record set when records are supplied.
10. **REST API** — the full surface over HTTP (see README endpoint
    table), with the house auth convention (X-User/X-Role against a
    demo registry; 401 unknown/mismatched, 403 permission, denied
    attempts audited).
11. **Access control (RBAC)** — admin/steward/viewer matrix enforced
    in the store before any state change or id allocation, and again
    at the service layer.
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation, every search, and every denied attempt
    (`<action>:denied`).

**Reuse, stated explicitly:** the implementation in `src/` and the
suite in `tests/` are the shipped Group 12 (Data Management L2)
build's code, reused — this project's own Apache-2.0 code. A per-file
hash comparison (recorded in `scratch/reuse-note.md`) shows all 7
`src/` modules and 12 of 14 test files byte-identical to Group 12's;
the two differing test files differ in documentation wording only
(the helpers' module docstring, and the negative control's traced-
claim wording, re-anchored from Group 12's sibling claim to this
group's carried design rule — no test logic changed). **What is NOT
reused is the baseline claim.** Group 12's Moderate / 800-171
framing does not carry over: this group's spec, traceability, and
README are written against the Low baseline and FAR 52.204-21 only,
and no control is claimed here on the strength of Group 12's spec.

## Control baseline (traceability) — Low / L1, the lightest tier

- **Group tier:** CMMC **L1** ⇔ FedRAMP **LI-SaaS** (this fork's
  impact level) per `../../crosswalk.md`.
- **Baseline source:** NIST SP 800-53 Rev. 5 **Low** baseline. LI-SaaS
  is FedRAMP's tailored **subset** of that baseline for SaaS
  offerings, so the union of this group's parent baselines is the
  Low baseline itself, cross-walked to the 17 practices of **FAR
  52.204-21** that define CMMC L1. One parent, so no merge changes
  the tier (Merge Rules 1 and 2 are satisfied trivially — recorded
  anyway, so the record shows the step was taken, not skipped).
- **Feature → control family mapping (this build, at the Low
  baseline):**

| Core function | Control families | How the build answers |
|---|---|---|
| Dataset registry, schema | CM-6, SI-10, AC-3 | Datasets and schemas are explicit, validated configuration records; nothing is described that is not registered |
| Catalog search | AC-3 | Review over registered metadata only, permission-gated; the search's audit recording rides on the audit log (AU, FedRAMP-Low side — see audit row) |
| Sources, ingestion, provenance | AU-2, AU-3 (Low side), SI-12 | Every arrival of data is an auditable record with source, counts, and status |
| Quality rules & checks | SI-10, CA-2 | Deterministic validation of supplied records against registered rules; check results are stored assessments |
| Access governance | AC-3, IA-2 (hooks) | Purpose-bound requests, time-boxed grants, revocation; on the FAR side, the access-limitation practices (limit access to authorized users, transactions, and functions). Precision note below on separation of duties |
| Retention schedules | SI-12 | Retention is policy recorded in advance; due state is computed, disposition execution is Extended |
| Export manifests | AU-2, AU-3 (Low side), SC-8 (partial) | Exports are auditable events with checksums; transmission protection is TLS-when-configured (see gaps) |
| RBAC | AC-2, AC-3, IA-2 (hooks) | Three-role matrix enforced pre-mutation at two layers; identity supplied by the embedding organization |
| Audit log | AU-2, AU-3 — **FedRAMP Low side only** | Append-only log including denied attempts; no mutation API. Precision note below |

- **Precision notes (what Low does not carry, stated so nothing is
  silently imported from Group 12's Moderate table):**
  - **Audit:** CMMC L1 / FAR 52.204-21 contains **no audit
    practice**, so no audit claim is made on the CMMC side. The
    audit log is carried because the FedRAMP Low baseline (and its
    LI-SaaS tailoring) carries the AU family — Group 12's AU-6
    (audit review) and AU-9 (protection of audit information)
    citations are Moderate selections and are **not** claimed here;
    AU-2/AU-3 only.
  - **Separation of duties:** the never-self-approve guard is a
    design property of the carried substrate (it is the group's
    negative control). Its control-family home is AC-5, but AC-5 —
    and AC-6 — are not Low-baseline selections, so the guard is
    traced to AC-3 access enforcement at this tier, with AC-5 named
    as lineage only. Group 12's AC-5/AC-6 citations do not carry
    down.
  - **What else does not carry down:** the Moderate/High apparatus
    from the sibling Data Management groups (800-171 depth; the
    L3 group's audit-chain uplift, lockout machinery, and
    800-172-derived enhancements) is out of scope for a Low/L1
    build and is not inherited downward.
- **Caveat (standing, from crosswalk.md):** this traceability is a
  planning/matching mapping. The build is not a FedRAMP
  authorization and confers no CMMC certification; it is an
  open-source implementation whose features trace to the Low/L1
  control families.

## Implementation contract (summary)

Identical to Group 12's — `src/datamgmt/` (Python stdlib only):
`errors` (`DataMgmtError`, `ValidationError`, `NotFoundError`,
`PermissionDenied`), `access` (User, admin/steward/viewer matrix),
`audit` (append-only AuditLog), `store` (DataMgmtStore: the 12 core
functions; failed operations consume no ids; permission checks
precede mutation; the self-approval guard lives in the single method
`_check_decider_not_requester`), `service` (HTTP layer, demo
registry alice=admin / bob=steward / carol=viewer), `__main__`
(`python -m datamgmt serve`, port 8792). `tests/`: 196 unittest
tests across 13 modules, every test docstring tracing to a core
function or a control family; the negative control and its live
mutation verification for this group are recorded in
`tests/README.md` (self-approval guard mutant → exactly 4 failures,
the same four as Group 12's drill; restored SHA-256-identical,
suite green).

## Coverage statement (for this build)

- Forks spec'd: **1 / 1** (Pagefreezer Website Archiving, LI-SaaS,
  its actual impact level recorded in the spec sheet).
- Claims evidenced for the fork: **0** of 19 families — stated, not
  rounded up (see `scratch/ARTIFACTS.md`).
- Core implemented: **12 / 12** functions above — **carried as the
  category substrate under the core-boundary decision, not claimed
  as this fork's evidenced functions.** The distinction is the
  coverage statement, not a footnote to it.
- Tests: **196 run, 196 passed**, including the mutation-verified
  negative control performed against this group's tree.

## Gaps — specified, not implemented (for the GAPS.md final batch)

This fork's own engines (new with this group):
- Web crawling & snapshot capture engine — the fork's central
  product function: crawling customer websites and capturing
  page snapshots. The substrate records ingestions; it captures
  nothing.
- Web page rendering for capture — rendering dynamic/JavaScript
  pages so snapshots reflect what a visitor sees.
- Change detection & dynamic monitoring engine — detecting new
  pages and changes to existing pages between captures (the
  description's "dynamic monitoring").
- Archive storage, sealing & replay — durable storage of captured
  pages with integrity sealing, and faithful playback/replay of
  the archive. (The substrate holds registry metadata and records,
  not captured content.)
- Full-content search & indexing over the archive — search across
  captured page content; the core's search is over registry
  metadata only.

Extended families carried from the category union (Group 12's list,
registered there; restated here so this group's record is complete):
- Distributed storage engines: data lake / warehouse internals,
  database engines, replication.
- Integration runtime & connector engine: live connectors,
  transformation execution, automation runtime.
- Privacy-preserving record-linkage engine: PPRL cryptography,
  universal-key matching, de-identified cohort computation;
  de-identification engines generally.
- Enterprise search indexing engine: full-text indexing at scale.
- Content processing engines: OCR, audio/video transcription,
  automated categorization.
- Workflow / BPM execution engine and guided-interview engine:
  adaptive forms, interview execution, stakeholder routing.
- Query & visualization engines: live query against source data
  and in-workflow report rendering.
- IaaS/PaaS hosting: compute, private cloud, virtual desktops,
  co-location, authorization inheritance.
- Kubernetes provisioning & cluster lifecycle engine.
- Asset inspection & capital-planning applications.
- Managed file transfer transport: protocol endpoints and
  regulated exchange rails.
- Case management depth: background investigation tracking,
  continuous vetting, adjudication workflows.
- AI/ML analytics & orchestration in bundled applications.
- Field-level / transformation lineage & provenance beyond
  ingestion records (claimed by no sibling by name at any tier;
  specified so the absence is a finding).
- Retention disposition execution: deletion/archival engines and
  NARA/FOIA production; the core schedules and reports due state
  only.

Platform layer (gap-listed, never implied closed): encryption at
rest (deployment layer); TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment);
demo identities are hooks, not an IdP — IA-2 stays with the
embedding organization.
