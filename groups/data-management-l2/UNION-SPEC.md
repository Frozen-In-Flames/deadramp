# Union Spec — Data Management, CMMC L2 (DeadRamp Phase 2, Group 12)

The merged functional spec for the Data Management sibling group at the
L2 tier: **8 forks, all FedRAMP Moderate**, reconciled zero-diff three
ways (`specs/specs.json` ↔ `forks.json` ↔ MAP.md "Data Management —
L2 (8)"), re-verified by the coordinator with `scratch/verify.py`.

The group: PMP Government-Gateway (Bamboo Health, Inc.) · Boomi
Enterprise Platform (Boomi, Inc.) · Asset Management Suite (AMS)
(Bridge Intelligence LLC. dba AssetIntel) · Collabspace (Collabware) ·
Datavant Cloud (Datavant) · Intelliworx Cloud Workflow Platform
(Intelliworx) · GovPoint Cloud Services (MIS Sciences Corporation) ·
Palette VerteX (Spectro Cloud).

This is a heterogeneous group. The source's "Data Management" category
collects a privacy-preserving health-data linkage platform, a records
and NARA-compliance platform, an enterprise integration platform, a
workflow/data-collection platform, a transportation asset suite, an
EHR prescription-data gateway, an IaaS/PaaS/SaaS hosting bundle, and a
Kubernetes provisioning platform. There is no single product they all
are. What the claim counts below prove they share is a **governance
substrate**: datasets held in a registry with schemas, data arriving
through recorded ingestion from registered sources, quality rules
checked against the data, access granted through requests and
approvals rather than by default, retention scheduled in advance, and
exports recorded — all under role-based access control with an audit
trail. The merged build implements that substrate; each vendor's
engine on top of it (linkage cryptography, integration runtimes,
search indexes, cluster provisioning, hosting) is an Extended
function, named in the gaps.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was sentence-split
and matched against a 19-family taxonomy defined from this category's
descriptions. A family is claimed only when the offering's own
description contains matching text; the first matching sentence is
stored in `specs/specs.json` as evidence, so every claim is
auditable. **28 claims survived.** Six wording-artifact corrections
were needed and are documented in `scratch/ARTIFACTS.md` (37 raw hits
→ 28): AssetIntel's Azure implementation-substrate sentence (its own
hosting stack, not customer-facing functions), bare "lifecycle"
splitting correctly into asset lifecycle (AMS) versus retention
(Collabspace) with no cross-claims, a considered-and-rejected
`audit_monitoring` family (AMS's Datadog log-forwarding is
vendor-operational logging of the offering itself), workflow
over-matching (a clinician's EHR "workflow", a bare "workflow" list
noun, cluster-provisioning "automates"), GovPoint's "inherited
controls" compliance posture, and Boomi's AI business-category (its
description text asserts no AI function; claims come from description
text only). **No fork has zero claims.** Per-fork claim counts:
Datavant Cloud 7, GovPoint Cloud Services 6, Collabspace 5,
Intelliworx Cloud Workflow Platform 5, Boomi Enterprise Platform 2,
PMP Government-Gateway 1, Asset Management Suite (AMS) 1, Palette
VerteX 1. All counts are a floor: several descriptions are boundary
prose or a single marketing sentence (Boomi's is one sentence), and
the floor is reported, not padded.

## Function ranking — all 8 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 4 | Integration, connectivity & data exchange | Core (sources, ingestion, export, API substrate); connector/runtime engines Extended |
| 2 | 2 | Dataset, records & repository registry | **Core** — dataset registry |
| 2 | 2 | Catalog search & discovery | **Core** — metadata search; indexing engines Extended |
| 2 | 2 | Ingestion & data collection | **Core** — ingestion records; collection engines Extended |
| 2 | 2 | Workflow, automation, review & approvals | Extended — engines; the approval substrate is Core (access governance) |
| 2 | 2 | Query, reporting & analytics | Core (records/provenance substrate); query/visualization engines Extended |
| 2 | 2 | Asset, cluster & infrastructure lifecycle management | Extended — domain applications (AMS, Palette VerteX) |
| 8 | 1 | Record linkage & matching | Extended — PPRL engine (Datavant) |
| 8 | 1 | Data governance & access controls | **Core** — access requests, decisions, grants |
| 8 | 1 | Privacy preservation & de-identification | Extended — de-identification engines |
| 8 | 1 | Retention, disposition & records lifecycle | **Core** — schedules + due evaluation; disposition execution Extended |
| 8 | 1 | Content processing (OCR, transcription, categorization) | Extended — processing engines |
| 8 | 1 | Data quality, accuracy & completeness validation | **Core** — quality rules + check runs |
| 8 | 1 | Guided data collection (forms & intelligent interviews) | Extended — interview engine; submissions are ingestion-shaped records |
| 8 | 1 | API / programmatic access | **Core** — REST API |
| 8 | 1 | Cloud platform hosting (compute, storage, private cloud) | Extended — IaaS/PaaS (GovPoint) |
| 8 | 1 | Case management & adjudication | Extended — ABIS depth inside the GovPoint bundle |
| 8 | 1 | Managed file transfer | Extended — transport (Sharetru inside GovPoint); transfers are ingestion-shaped records |
| 8 | 1 | AI/ML analysis & orchestration | Extended — models (GovPoint bundle applications) |

Named absences: **storage/database engines are claimed as a
customer-facing function by no sibling's description** — the only
storage text in the group is AssetIntel describing its own Azure
implementation substrate, corrected out above — so no storage family
exists in this union and the build holds metadata and records, not a
database engine. **Field-level lineage is claimed by no sibling**;
the build's provenance is at ingestion granularity (which sources fed
which dataset, when, how much), and transformation lineage is an
Extended gap, recorded as such rather than implied.

## The Core — what the merged build implements (12 functions)

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
   actives, and revoked. This is Datavant's "right entity, right
   purpose, right conditions" claim as substrate.
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

## Control baseline (traceability)

The group is uniformly **FedRAMP Moderate**, so the union baseline is
the tailored **NIST SP 800-53 Rev. 5 Moderate** baseline ⇔ the 110
practices of **NIST SP 800-171** behind CMMC L2, per `crosswalk.md`.
No parent carried a higher or lower baseline, so the merge changes
no tier.

| Core function | Control families | How the build answers |
|---|---|---|
| Dataset registry, schema | CM-6, SI-10, AC-3 | Datasets and schemas are explicit, validated configuration records; nothing is described that is not registered |
| Catalog search | AU-6, AC-3 | Review over registered metadata only, permission-gated |
| Sources, ingestion, provenance | AU-2, AU-3, SI-12 | Every arrival of data is an auditable record with source, counts, and status |
| Quality rules & checks | SI-10, CA-2 | Deterministic validation of supplied records against registered rules; check results are stored assessments |
| Access governance | AC-3, AC-5, AC-6, IA-2 (hooks) | Purpose-bound requests, separation of duties (no self-approval), time-boxed grants, revocation |
| Retention schedules | SI-12 | Retention is policy recorded in advance; due state is computed, disposition execution is Extended |
| Export manifests | AU-2, AU-3, SC-8 (partial) | Exports are auditable events with checksums; transmission protection is TLS-when-configured (see gaps) |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Three-role matrix enforced pre-mutation at two layers |
| Audit log | AU-2, AU-3, AU-9 | Append-only log including denied attempts; no mutation API |

**Caveat (standing, from crosswalk.md):** this traceability is a
planning/matching mapping. The build is not a FedRAMP authorization
and confers no CMMC certification; it is an open-source implementation
whose features trace to the Moderate/L2 control families.

## Implementation contract (summary)

`src/datamgmt/` (Python stdlib only): `errors` (`DataMgmtError`,
`ValidationError`, `NotFoundError`, `PermissionDenied`), `access`
(User, admin/steward/viewer matrix), `audit` (append-only AuditLog),
`store` (DataMgmtStore: the 12 core functions; failed operations
consume no ids; permission checks precede mutation; the self-approval
guard lives in the single method `_check_decider_not_requester`),
`service` (HTTP layer, demo registry alice=admin / bob=steward /
carol=viewer), `__main__` (`python -m datamgmt serve`, port 8792).
`tests/`: 196 unittest tests across 13 modules, every test docstring
tracing to a core function, a sibling claim, or a control family; the
negative control and its live mutation verification are recorded in
`tests/README.md` (self-approval guard mutant → 4 failures; restored
SHA-256-identical, suite green).

## Coverage statement (for this build)

- Forks spec'd: **8 / 8**, each with evidenced claims (28 total).
- Core implemented: **12 / 12** functions above.
- Tests: **196 run, 196 passed**, including the mutation-verified
  negative control.

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions:
- Distributed storage engines: data lake / warehouse internals,
  database engines, replication (no sibling claims a storage engine
  as a customer-facing function; the substrate holds metadata and
  records).
- Integration runtime & connector engine (Boomi): live connectors,
  transformation execution, automation runtime.
- Privacy-preserving record-linkage engine (Datavant): PPRL
  cryptography, universal-key matching, de-identified cohort
  computation; de-identification engines generally.
- Enterprise search indexing engine (Collabspace): full-text indexing
  at scale; the core's search is over registry metadata.
- Content processing engines (Collabspace): OCR, audio/video
  transcription, automated categorization.
- Workflow / BPM execution engine and guided-interview engine
  (Intelliworx): adaptive forms, interview execution, stakeholder
  routing; the core carries collection as ingestion records and
  approvals as access governance.
- Query & visualization engines (Bamboo Health PMP): live query
  against EHR data and in-workflow report rendering.
- IaaS/PaaS hosting (GovPoint): compute, private cloud, virtual
  desktops, co-location, Authorization-as-a-Service inheritance.
- Kubernetes provisioning & cluster lifecycle engine (Spectro Cloud
  Palette VerteX): cluster provisioning, blueprint stacks, day-2
  operations.
- Asset inspection & capital-planning applications (AssetIntel AMS):
  inspection workflows, emergency response, capital planning over
  transportation assets.
- Managed file transfer transport (Sharetru, inside GovPoint):
  protocol endpoints and regulated exchange rails.
- Case management depth (ABIS, inside GovPoint): background
  investigation tracking, continuous vetting, adjudication workflows.
- AI/ML analytics & orchestration in the GovPoint bundle
  applications (GRID20/20 ATI, NXXUS).
- Field-level / transformation lineage & provenance beyond ingestion
  records (claimed by no sibling by name; specified here so the
  absence is a finding).
- Retention disposition execution: deletion/archival engines and
  NARA/FOIA production (Collabspace); the core schedules and reports
  due state only.

Platform layer (gap-listed, never implied closed): encryption at rest
(deployment layer); TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment);
demo identities are hooks, not an IdP — IA-2 stays with the embedding
organization.
