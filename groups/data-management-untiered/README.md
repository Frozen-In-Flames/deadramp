# Data Management — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **8 untiered forks** of Data Management —
census unit `untiered:Data Management` in `../../remainder.json`.
**This is an untiered set, and that means something specific:**
every member's FedRAMP impact level is **Unknown** in the source
dataset. The source publishes no baseline for these offerings, so
**tier stays null**: no tier is assigned, no CMMC equivalence is
drawn, and this build asserts **no control baseline**. Per
PIPELINE.md, untiered offerings "build to their documented control
claims; tier stays null in the registry until the source publishes
a baseline." The union contract is
[`UNION-SPEC.md`](UNION-SPEC.md); per-fork spec sheets are in
[`specs/specs.json`](specs/specs.json), each recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The 8 forks were spec'd under the category's existing 19-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Data Management L2 group's original
shipped claim tables exactly — **8 of 8 forks, 28 of 28 claims,
deep-equal** — before tagging this set. Result here: **13 claims**
across the set, **6 of 8 forks claiming at least one**; the two
zero-claim forks (Files.com and OATI Marketplace) are recorded
under Named absences in the union spec, not hidden or repaired.

The build implements the category's **twelve-function substrate**
— the governance records machinery the founding group established —
carried **byte-identical** from the founding Data Management L2
build (`../data-management-l2/src/datamgmt/`, 7 of 7 modules;
SHA-256 accounting below). The substrate is tier-independent
records code: the founding source contains no tier or baseline
machinery, so there was nothing tier-shaped to strip. Where the
founding contract's text ties functions to the Moderate/L2
baseline, read it here as **baseline-neutral substrate**, claimed
against no baseline. Claim support in this set is stated per
function in the union spec: 4 of the 12 functions are
claim-supported by a taxonomy family here; 8 are carried substrate
(including access governance, whose family has zero claimants in
this set — see Honesty).

## The 8 forks

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2700429895 | Ardoq Inc | Ardoq | 2 |
| FR2630354495 | Files.com | Files.com | 0 |
| FR2629068833 | Immuta | Immuta Federal | 1 |
| FR2702058502 | Ocient Inc. | OcientAIQ | 2 |
| FR2629068832 | Open Access Technology International, Inc. | OATI Marketplace | 0 |
| FR2634450946 | Pinecone Systems, Inc. | Pinecone | 2 |
| FR2631654537 | Wisedocs USA Inc. | Wisedocs for Government | 1 |
| FR2504771625 | ZL Technologies, Inc. | ZL Unified Archive (ZL UA) | 5 |

In `forks.json` the set is mixed as filed: 4 forks carry the Data
Management category, 2 are filed under Artificial Intelligence
(AI), 1 under Analytics, and 1 as "Uncategorized (none in
source)"; the census assigned all 8 to Data Management from their
own descriptions, and the spec sheets record the assignment.
Authorization statuses as recorded span FedRAMP Certified (2),
Initial Implementation (5), and Legacy FedRAMP Ready (1) — a
status is record data, not a claim.

## The 12 core functions

1. **Dataset registry** — datasets (`ds-`) with owner,
   classification (`public` / `internal` / `cui` / `phi`), tags,
   and a versioned schema (each field: name, type, required,
   sensitive). Updating the schema increments `schema_version`.
2. **Catalog search** — literal, case-insensitive substring search
   over datasets (name, description, tags, schema field names),
   sources, and quality rules.
3. **Source registry** — data sources (`src-`) by kind (`file`,
   `database`, `api`, `stream`, `manual`) with a location.
4. **Ingestion records** — ingestion runs (`ing-`) recording
   dataset, source, mode (`full` / `incremental` / `stream`),
   record counts, checksum, and `completed` / `failed` status.
5. **Provenance view** — for any dataset: the sources that fed it,
   its ingestion runs, and its total records over completed runs.
   Provenance at ingestion granularity; field-level lineage is an
   Extended gap.
6. **Data quality** — quality rules (`qr-`) of five kinds
   (`completeness`, `uniqueness`, `format`, `range`, `freshness`)
   and check runs (`qc-`) evaluating a rule against a supplied
   batch of records with deterministic violation semantics.
7. **Access governance** — purpose-bound access requests (`ar-`),
   decisions by someone who is never the requester, time-boxed
   grants (`gr-`) on approval, active-grant queries, and
   revocation.
8. **Retention schedules** — one retention policy (`rp-`) per
   dataset (retention days, disposition `delete` / `archive` /
   `review`, legal hold) plus a due evaluation against the
   dataset's latest completed ingestion (or its creation). The
   build schedules and reports; it does not execute disposition.
9. **Export manifests** — export records (`ex-`) with format,
   record count, schema version, and a SHA-256 checksum of the
   canonical record set when records are supplied.
10. **REST API** — every function above over a JSON REST API.
11. **RBAC** — roles `admin`, `steward`, `viewer` with a
    permission matrix enforced on every operation (see below).
12. **Append-only audit log** — every mutation, every search, and
    every denied attempt, with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence. There is no
    mutation or deletion API for audit entries.

Malformed input is rejected with a validation error and leaves the
store completely unchanged (no partial application, no id
consumed). Ids are sequential per object type: `ds-`, `src-`,
`ing-`, `qr-`, `qc-`, `ar-`, `gr-`, `rp-`, `ex-`.

**The pointers-only boundary:** the build holds metadata and
records *about* data — dataset records, source locations, ingestion
facts, checksums. It stores **no fork content and no content from
any dataset**: there is no data store in it. Records supplied to a
quality check or an export call are evaluated or checksummed in
that call under the founding contract; the registry itself keeps
pointers, counts, and hashes, never payloads.

## How to run

From this directory:

```sh
PYTHONPATH=src python3 -m datamgmt serve            # http://127.0.0.1:8792
PYTHONPATH=src python3 -m datamgmt serve --port 9000 --audit-log audit.jsonl
PYTHONPATH=src python3 -m datamgmt serve --certfile cert.pem --keyfile key.pem   # TLS
```

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied
per request with the `X-User` and `X-Role` headers. The role
header must match the registry exactly, or the request is rejected
with 401 (an unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | everything, including reading the audit log |
| `bob`   | steward | all reads except the audit log; all writes incl. access decisions |
| `carol` | viewer  | reads (except the audit log) and requesting access |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client. Denied attempts are audited with the action suffixed
`:denied`.

## API endpoints

| Method & path | Action | Notes |
|---|---|---|
| `GET /health` | — | no auth; `{"status": "ok"}` |
| `GET /audit` | audit_read | admin only; `{"entries": [...]}` |
| `GET /search?q=` | catalog_read | `{"datasets": [...], "sources": [...], "quality_rules": [...]}` |
| `GET /datasets` · `POST /datasets` | dataset_read / dataset_write | create → 201 |
| `GET /datasets/{id}` · `POST /datasets/{id}` | dataset_read / dataset_write | POST updates metadata |
| `POST /datasets/{id}/schema` | dataset_write | bumps `schema_version` |
| `GET /datasets/{id}/ingestions` · `POST` | ingest_read / ingest_record | |
| `GET /datasets/{id}/provenance` | ingest_read | sources + runs + total records |
| `GET /datasets/{id}/quality-rules` · `POST` | quality_read / quality_write | |
| `GET /datasets/{id}/access-requests` · `POST` | access_read / access_request | |
| `GET /datasets/{id}/exports` · `POST` | dataset_read / export | |
| `GET /datasets/{id}/retention-policy` · `POST` | retention_read / retention_write | GET 404s when no policy set |
| `GET /sources` · `POST /sources` · `GET /sources/{id}` | source_read / source_write | |
| `GET /ingestions/{id}` | ingest_read | |
| `GET /quality-rules/{id}` | quality_read | |
| `POST /quality-rules/{id}/checks` · `GET` | quality_run / quality_read | body `{"records": [...], "now": ...}` |
| `GET /quality-checks/{id}` | quality_read | |
| `GET /access-requests` · `GET /access-requests/{id}` | access_read | |
| `POST /access-requests/{id}/decide` | access_decide | body `{"approve": true, "reason": ...}`; never the requester |
| `GET /grants` (`?dataset_id=`, `?grantee=`) · `GET /grants/{id}` | access_read | |
| `POST /grants/{id}/revoke` | access_decide | |
| `GET /retention-policies` · `GET /retention-policies/{id}` · `POST /retention-policies/{id}` | retention_read / retention_write | POST updates |
| `GET /retention-due` (`?now=`) | retention_read | `{"due": [...]}` |
| `GET /exports/{id}` | dataset_read | |

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**202 tests, OK** at delivery: the founding group's 196-test core
suite carried with the code, plus spec tests pinning this set
(exactly 8 sheets; membership exact against `remainder.json`;
every sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; 13 claims total with exactly two
zero-claim forks). The category's signature self-approval-guard
mutation drill was re-run in this tree — exactly 4 failures under
the mutant, store restored and SHA-256 verified (see
`tests/README.md`).

## Byte-identity accounting

`src/datamgmt/` is carried from the founding group
`../data-management-l2/src/datamgmt/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `e9eb1b4c9f7ba3bf8dee78acf6ae8a3712d9b553a1c1d4880eae14ca5b688cd1` |
| `__main__.py` | `b169b52941e2b0875205a62f88c95dc3b5ffeef5440d892d75232e9614016ec5` |
| `access.py` | `805d4c25dd9a399123fbd2b524956b60619c6b11493abb630f10ccb9471fd1e5` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `f2cf919b5110244e30c0bc8a3a6a497f64e51b5b75f9b2c3f0231d877ff20f55` |
| `service.py` | `f11f1c9e37024fb4257e4559075deabd955029fe1def381e3abfe0e2e622e728` |
| `store.py` | `dc35677ccdaf4d416a10a5364128f54bb1b1802fd8a99c00271ad081caf2774e` |

The test suite is likewise carried (the founding suite minus its
additions module, which pins a different census unit), with one
labeling fix in `tests/datamgmt_helpers.py` (its docstring now
names this untiered set instead of L2) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for these 8 offerings (all "Unknown"), so
this build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the forks' own
marketplace descriptions assert, in their own words. A documented
control claim is a **fork's claim about itself**, recorded with
its evidence in `UNION-SPEC.md` and `specs/specs.json`; it is not
the build's control attainment, and nothing here fills a family
in from any baseline. Two layers, kept distinct: the taxonomy
layer (control language that fired a family) and the prose tier
(control language asserted in sentences that fired no family —
documented so the posture is visible, never converted into
taxonomy claims).

Documented via a taxonomy family:

- **Information management & retention (SI-12)** — 1 fork, via
  `retention_disposition`: ZL Unified Archive (records capture,
  storage, retention, and disposition under the Federal Records
  Act and NARA requirements it names).

Documented at the prose tier:

- **Access control (AC)** — Immuta (attribute-based access and
  control, warehouse-side policy enforcement, temporary scoped
  agent roles auto-removed on task completion); ZL Unified Archive
  (access restricted to authorized agency personnel).
- **Identification & authentication (IA)** — Immuta (SSO and
  directory-controlled authentication); ZL Unified Archive
  (exports gated on an agency-approved identity management
  system).
- **Audit (AU)** — Immuta (platform auditing and a dual-identity
  audit trail for agent activity); ZL Unified Archive (a complete
  audit log of actions on documents). This taxonomy has no audit
  family by the founding group's deliberate design, so no audit
  *function* is claimed for any fork; the build's own audit log is
  substrate.
- **Cryptographic protection (SC)** — Pinecone (AES-256 encryption
  at rest with per-object keys, TLS 1.2 in transit); ZL Unified
  Archive (encrypted content storage). The build performs no
  cryptography of its own.

**Not documented** by any fork in this set: every other NIST SP
800-53 control family — including AT, CA, CM, CP, IR, MA, MP, PE,
PL, PM, PS, RA, and SA, and SI beyond the retention sentence — is
asserted by no description in the set. If the source later
publishes an impact level for any of these offerings, the tier is
recorded then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for any fork or for itself.
  The forks' recorded authorization statuses are source data, not
  claims by this build, and a fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **No fork content is ever stored.** The registry holds metadata
  records carrying pointers (source locations), counts, and
  checksums — never payloads. There is no data store, no storage
  engine, and no database engine in this build; retention is
  scheduled and reported, not executed, and quality checks
  evaluate only the records supplied in the call.
- **Extended functions are specified, not implemented.** The
  union spec ranks 19 functions; the substrate behind 12 is
  implemented here. NOT implemented (claimant counts are this
  set's): AI/ML analysis & orchestration engines (6 — the build
  ships no model); a vector database & embedding index engine
  (Pinecone — this build's search is literal substring over
  registry metadata, not similarity retrieval); document
  processing engines — OCR, classification, duplicate detection
  (Wisedocs, a described function that earned no taxonomy claim);
  a petabyte-scale warehouse & analytics engine (OcientAIQ); an
  enterprise architecture graph platform (Ardoq); a policy
  enforcement plane / ABAC engine inside customer data platforms
  (Immuta — described, with no data-governance claim under the
  verbatim taxonomy); a managed file transfer transport
  (Files.com, zero claims); archive / eDiscovery / FOIA
  production including disposition execution (ZL); enterprise
  search indexing engines (2); query & visualization engines (1);
  and the standing category engines with no claimant here
  (integration runtimes, record-linkage and de-identification
  engines, workflow/BPM and guided-interview engines, hosting,
  case management, cluster lifecycle, field-level lineage).
- **The build performs no cryptography of its own.** Two forks
  document encryption claims about themselves; the substrate does
  no encryption — TLS is a deployment-layer option when a
  certificate is configured, and FIPS-validated crypto (SC-13) is
  not claimed by the build.
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own. IA-2 stays with the embedding
  organization.
- **Named absences stand.** Data governance has 0 claimants in
  this set (Immuta's prose never uses the family's phrases);
  API/programmatic access has 0 (despite API prose in four
  descriptions); content processing has 0 (Wisedocs spells out
  "optical character recognition"); data quality validation has
  0; integration & exchange has 0; managed file transfer has 0;
  and two forks (Files.com, OATI Marketplace) carry zero claims
  at all. Nothing was back-filled to make the set look complete.
