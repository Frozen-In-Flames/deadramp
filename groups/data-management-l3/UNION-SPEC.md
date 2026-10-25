# Union Spec — Data Management, CMMC L3-adjacent (DeadRamp Phase 2, Group 28)

The merged functional spec for the Data Management sibling group at
the L3-adjacent tier: **2 forks, all FedRAMP High**, reconciled
zero-diff three ways (`specs/specs.json` ↔ `forks.json` ↔ MAP.md
"Data Management — L3-adjacent (2)"), re-verified by the coordinator
with `scratch/verify.py`.

The group: US Axon FedCloud - High (Axon) · Kiteworks Secure Gov
Cloud (Kiteworks USA, LLC).

## Lineage: a cross-tier merge (the Merge Rule applied across tiers)

This build does not start from zero. It is the merge of two parents:

1. The **Group 12 merged build** (`../data-management-l2/`) — itself
   the union of the 8 Data Management L2 (FedRAMP Moderate) forks,
   shipped as a working clean-room data-governance service.
2. This group's **2 High forks**, via the spec sheets in `specs/`.

Per the Merge Rule (`../../crosswalk.md`, Merge Governance): the
merge takes the **union** of the parents' baselines (Rule 1), the
merged fork inherits the **highest** tier — FedRAMP **High** / CMMC
**L3-adjacent** — and must satisfy it **in full** (Rule 2), this
document plus the spec sheets are the **traceability** record
(Rule 3), and the build followed the SSDF-shaped process of
provenance (this lineage), review, and verification before being
treated as satisfying the tier (Rule 4): the full suite was run by
the coordinator, and the negative controls were mutation-verified
(see Verification).

**Reuse, stated explicitly:** this build reuses Group 12's own
open-source code (Apache-2.0, ours). One module is byte-identical to
Group 12 (`__init__.py`); six are modified for the tier uplift
(`audit.py`, `access.py`, `store.py`, `service.py`, `errors.py`,
`__main__.py`). The uplift analysis below names what the High
baseline demanded beyond the L2 core and what was done about each
item — implemented, or gap-listed by name.

## How functions were counted

Each fork's public marketplace description (GSA FedRAMP Marketplace
dataset, cached at `raw/data_dump.json`; produced by the General
Services Administration, last change 2026-10-22) was matched against
**Group 12's 19-family taxonomy, verbatim** — same ids, labels, and
matching patterns — so counts are comparable across tiers. A family
is claimed only when the offering's own description contains
matching text; the first matching sentence (or, for Kiteworks'
bulleted list, the matching line) is stored in `specs/specs.json` as
evidence, so every claim is auditable. **6 claims survived** of 7 raw
hits: one wording-artifact correction was applied and is documented
in `scratch/ARTIFACTS.md` (Kiteworks' "Virtual private cloud (VPC)
environment" is the offering's own deployment substrate, not
hosting sold as a customer-facing function — the direct analogue of
Group 12's AssetIntel Azure-substrate correction). **Neither fork
has zero claims** (3 each). Six further near-misses — functions both
descriptions assert in substance but the verbatim patterns do not
fire on (Kiteworks' REST APIs and governance prose, Axon's
"integrates" / "connect" verb choices and device-control domain) —
are itemized in `scratch/ARTIFACTS.md`, recorded rather than
repaired: the taxonomy was not re-tuned for this group. All counts
are a floor.

## Function ranking — all 2 siblings

| # | Forks | Function family | Disposition |
|---|---:|---|---|
| 1 | 1 | Dataset, records & repository registry (Axon) | **Core** — dataset registry |
| 1 | 1 | Catalog search & discovery (Axon) | **Core** — metadata search; indexing engines Extended |
| 1 | 1 | Ingestion & data collection (Axon) | **Core** — ingestion records; collection engines Extended |
| 1 | 1 | Integration, connectivity & data exchange (Kiteworks) | **Core** (sources, ingestion, export, API substrate); connector/runtime engines Extended |
| 1 | 1 | Retention, disposition & records lifecycle (Kiteworks) | **Core** — schedules + due evaluation; disposition execution Extended |
| 1 | 1 | Managed file transfer (Kiteworks) | Extended — transport; transfers are ingestion-shaped records in the core |
| — | 0 | Record linkage & matching | Extended (carried from the L2 union) |
| — | 0 | Data governance & access controls | **Core** — access governance (carried; see core-boundary note) |
| — | 0 | Privacy preservation & de-identification | Extended (carried) |
| — | 0 | Content processing (OCR, transcription, categorization) | Extended (carried) |
| — | 0 | Data quality, accuracy & completeness validation | **Core** — quality rules + check runs (carried) |
| — | 0 | Workflow, automation, review & approvals | Extended — engines; the approval substrate is Core (carried) |
| — | 0 | Guided data collection (forms & intelligent interviews) | Extended (carried) |
| — | 0 | Query, reporting & analytics | **Core** (records/provenance substrate, carried); query/visualization engines Extended |
| — | 0 | API / programmatic access | **Core** — REST API (carried; Kiteworks near-miss recorded) |
| — | 0 | Asset, cluster & infrastructure lifecycle management | Extended (carried) |
| — | 0 | Cloud platform hosting (compute, storage, private cloud) | Extended (carried); Kiteworks raw hit corrected out (substrate) |
| — | 0 | Case management & adjudication | Extended (carried) |
| — | 0 | AI/ML analysis & orchestration | Extended (carried) |

**Core-boundary note (the recorded decision, same as Groups 6, 22,
and 23):** 13 of the 19 taxonomy families tag zero claims in this
group, and six of the twelve Core functions rest on families with no
tagged claim here. They stay Core because the Merge Rule carries the
L2 union upward whole — the merged fork inherits the highest tier
and the full union of functions; a wording artifact (short or
list-format descriptions, verb choices the verbatim patterns do not
fire on) is not a downgrade. Dropping the governance substrate at
High because two High listings describe themselves tersely would
violate Rule 1 (union, never intersection).

**Group character, preserved rather than averaged away:** the two
members are not smaller versions of the L2 group's platforms. Axon
is a law-enforcement digital-evidence platform (evidence repository,
ingest and search over video/photo/document stores, a device fleet
of body-worn and in-car cameras and TASER devices behind it, plus
real-time operations and records/report automation). Kiteworks is a
secure content-communications enclave (file transfer and sharing
across web/email/SFTP/MFT/APIs, secure data forms, possessionless
editing, DLP/antivirus/SIEM integration, customer-managed keys,
audit logging and retention as compliance capabilities). What they
jointly presuppose at the High baseline is the governance substrate
the L2 union defines — registered datasets, recorded ingestion,
governed access, scheduled retention, audited everything — plus the
transfer and retention functions both name outright. Each vendor's
domain depth on top of that substrate is Extended, named in the
gaps.

## The Core — what the merged build implements (12 functions, at the High baseline)

Group 12's twelve functions, carried up whole:

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
   Provenance at ingestion granularity, honestly bounded (no sibling
   at either tier claims field-level lineage).
6. **Data quality** — quality rules (`qr-`) of five kinds
   (completeness, uniqueness, format, range, freshness) and check
   runs (`qc-`) that evaluate a rule against a supplied batch of
   records with pinned, deterministic violation semantics.
7. **Access governance** — access requests (`ar-`) with a stated
   purpose and duration; decisions by a steward or admin who is
   **never the requester** (self-approval is denied at a single named
   seam and is the group's inherited negative control); approvals
   mint time-boxed grants (`gr-`) that can be listed, filtered for
   actives, and revoked.
8. **Retention schedules** — one retention policy (`rp-`) per dataset
   (retention days, disposition delete/archive/review, legal hold)
   and a due evaluation referenced to the latest completed
   ingestion. The build schedules and reports; it does not execute
   disposition.
9. **Export manifests** — export records (`ex-`) with format, record
   count (supplied batch, or summed from completed ingestions), the
   dataset's schema version, and a SHA-256 checksum of the canonical
   record set when records are supplied.
10. **REST API** — the full surface over HTTP (see README endpoint
    table), with the house auth convention (X-User/X-Role against a
    demo registry; 401 unknown/mismatched, 403 permission, denied
    attempts audited), uplifted with logon lockout (AC-7, below).
11. **Access control (RBAC)** — admin/steward/viewer matrix enforced
    in the store before any state change or id allocation, and again
    at the service layer, plus the **`auditor`** role holding
    `audit_read` only (AC-5 uplift, below).
12. **Audit log** — append-only, JSONL-persistable, recording every
    mutation, every search, and every denied attempt
    (`<action>:denied`), uplifted with a **hash-chained
    tamper-evident** chain, chain verification, audit query/reduction,
    and **fail-closed** write behavior (AU-9/AU-7/AU-5, below).

## Control baseline and tier-uplift analysis (traceability)

- **Group tier:** CMMC **L3-adjacent** ⇔ FedRAMP **High** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **High** baseline (the
  FedRAMP High tailoring) ⇔ the CMMC L3 basis: the 110 practices of
  NIST SP 800-171 **plus** the selected NIST SP 800-172 enhanced
  requirements. Both parent forks sit at High, and the cross-tier
  parent (Group 12's build) sat at Moderate; the union baseline is
  therefore the High baseline, un-diluted (Merge Rule 1), inherited
  in full (Rule 2). "Adjacent" remains deliberate wording, as in the
  crosswalk: L3 is not identical to FedRAMP High; it is the same
  assurance weight class.

| Core function | Control families | How the build answers |
|---|---|---|
| Dataset registry, schema | CM-6, SI-10, AC-3 | Datasets and schemas are explicit, validated configuration records; nothing is described that is not registered |
| Catalog search | AU-6, AC-3 | Review over registered metadata only, permission-gated |
| Sources, ingestion, provenance | AU-2, AU-3, SI-12 | Every arrival of data is an auditable record with source, counts, and status |
| Quality rules & checks | SI-10, CA-2 | Deterministic validation of supplied records against registered rules; check results are stored assessments |
| Access governance | AC-3, AC-5, AC-6, IA-2 (hooks) | Purpose-bound requests, separation of duties (no self-approval), time-boxed grants, revocation |
| Retention schedules | SI-12 | Retention is policy recorded in advance; due state is computed, disposition execution is Extended |
| Export manifests | AU-2, AU-3, SC-8 (partial) | Exports are auditable events with checksums; transmission protection is TLS-when-configured (see gaps) |
| RBAC | AC-3, AC-5, AC-6, IA-5 (hooks) | Four-role matrix enforced pre-mutation at two layers; auditor role separates audit review from operations (AC-5) |
| Audit log | AU-2, AU-3, AU-5, AU-6, AU-7, AU-9 | Append-only log including denied attempts; hash-chained and tamper-evident (AU-9); fail-closed writes with store-level rollback (AU-5); query/reduction (AU-7); no mutation API |
| REST API auth | AC-7, IA-2 (hooks) | Per-username consecutive-failure lockout at the service layer (AC-7); identity itself is supplied by the embedding organization |

- **Uplift analysis — what High demanded beyond the L2 core:**

  | Demand (High / 800-172 direction) | L2 core state | This build |
  |---|---|---|
  | Protect audit information against tampering (AU-9, AU-3; 800-172 audit requirements) | Append-only store, no integrity proof | **Implemented**: every entry carries `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON (genesis `prev_hash` = `"0"*64`); `verify_chain()` recomputes the chain and localizes the first bad entry; exposed as `GET /audit/verify` |
  | Act on audit processing failure (AU-5) | A failed file write could diverge silently | **Implemented, fail closed**: `AuditLog.record()` rolls back the in-memory append and raises `AuditWriteError`; the store wraps every mutating method in a snapshot rollback (`_atomic`) so the whole operation rolls back (no object, no change, no id consumed) and the service propagates — an operation whose audit write fails does not proceed |
  | Audit review, analysis & reduction (AU-6, AU-7) | Full-trail read only | **Implemented**: `AuditLog.query(actor, action, target, since, until)` plus matching `GET /audit` filter parameters |
  | Unsuccessful logon attempts (AC-7) | No failure accounting | **Implemented**: per-username consecutive-failure tracking in the service; lockout at `max_failures` (default 3) for `lockout_seconds` (default 300); locked attempts return 403 and are audited as `auth:locked`; success resets the counter |
  | Separation of duties (AC-5) | Admin held every permission including audit review | **Implemented (technical slice)**: new `auditor` role (demo identity `dana`) holds `audit_read` and nothing else — audit review exists as a duty separable from administration and stewardship. Organizational SoD policy (who may hold which role) remains the embedding organization's, stated plainly |
  | Stronger authentication (IA-2(1)/(2) MFA & replay resistance, IA-5 authenticator management) | Header-supplied identity hooks | **Gap, named**: these are identity-provider properties. This build ships hooks, not an IdP (same posture as Group 12, restated because High demands more of the IdP layer — Kiteworks' own listing advertises MFA support and PIV/CAC/TOTP authenticators as product features of its identity layer, which is exactly the layer this build does not ship). The embedding organization must supply MFA-grade authentication |
  | FIPS-validated cryptography (SC-13) | Stdlib `ssl`/`hashlib` | **Gap, named**: Python's standard library is not a FIPS-validated cryptographic module. Validated crypto is a platform/deployment property and is **not claimed** here. (Kiteworks claims FIPS 140-3 validated modules as a product feature; this build does not inherit that claim.) |
  | Encryption at rest (SC-28) | Deployment-layer, stated not claimed | **Gap, unchanged**: remains a deployment-layer control |
  | Audit retention (AU-11) | Not addressed | **Gap, named**: no retention-period enforcement on the audit trail in this build (dataset retention schedules are Core function 8; audit-log retention rides with the platform layer) |
  | Session lock / termination (AC-11, AC-12) | Not addressed | **Gap, named**: the service authenticates per request from headers and holds no session state to lock or terminate; session management belongs to the embedding layer |

- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does
  not claim either.

## Implementation contract (summary)

`src/datamgmt/` (Python stdlib only), Group 12's contract unchanged
except for the uplift deltas marked **[L3]**:

- `datamgmt/errors.py` — `DataMgmtError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied`, plus **[L3]**
  `AuditWriteError`.
- `datamgmt/access.py` — roles `admin|steward|viewer` plus **[L3]**
  `auditor` = {`audit_read`}; `PERMISSIONS`/`ACTIONS` as Group 12
  otherwise; `require(user, action)` raises `PermissionDenied`.
- `datamgmt/audit.py` — `AuditLog(path=None)`; `.record(...)` →
  entry dict with keys `ts, actor, action, target, details` plus
  **[L3]** `seq, prev_hash, hash` (SHA-256 of the canonical JSON of
  `{seq, ts, actor, action, target, details, prev_hash}`); raises
  **[L3]** `AuditWriteError` and rolls the append back if the JSONL
  write fails. `.entries()` returns all entries. **[L3]**
  `.query(actor=None, action=None, target=None, since=None,
  until=None)` returns filtered entries; `.verify_chain()` returns
  `(ok, first_bad_index_or_None)`. Append-only; optional JSONL file;
  loaded entries participate in chain verification.
- `datamgmt/store.py` — as Group 12 (the 12 core functions; failed
  operations consume no ids; permission checks precede mutation;
  the self-approval guard lives in the single method
  `_check_decider_not_requester`); **[L3]** every mutating method
  runs inside the `_atomic` snapshot guard, so an audit write
  failure rolls the whole operation back and `AuditWriteError`
  propagates.
- `datamgmt/service.py` — `make_server(host, port, store, audit,
  users, max_failures=3, lockout_seconds=300)` **[L3 kwargs]**.
  Auth via `X-User` / `X-Role` headers (role must match the
  registry). **[L3]** consecutive auth failures are tracked per
  username; at `max_failures` the username locks for
  `lockout_seconds` (403, audited `auth:locked`); success resets.
  Endpoints as Group 12 plus **[L3]** `GET /audit/verify` →
  `{ok, entries, first_bad_index}` (audit_read) and `GET /audit`
  filter params `actor, action, target, since, until`. Errors are
  JSON `{error}` with 400/401/403/404 as applicable. Denied
  attempts are audited.
- `datamgmt/__main__.py` — `python -m datamgmt serve --host --port
  [--audit-log PATH] [--certfile --keyfile] [--max-failed-logins N]
  [--lockout-seconds S]` **[L3 flags]** with demo users
  `alice=admin, bob=steward, carol=viewer, dana=auditor` **[L3]**
  (documented as demo identities; production identity is the
  embedding organization's).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim / control family it traces to.
239 tests: the 196 Group 12 tests (inherited; three test files and
the shared helpers minimally adapted for the uplift — adaptations
listed in `tests/README.md` — plus one new auditor-matrix test in
`test_access.py`, for 197) plus
42 new tests covering the chain, audit query, fail-closed behavior,
lockout, and the auditor role. Two **negative controls**:

1. The self-approval guard mutant (carried from Group 12): the
   canonical expectation is shown to reject a requester deciding
   their own access request. Mutation-verified for this group by
   patching the real `_check_decider_not_requester` to a no-op: the
   suite failed with exactly 4 failures; the file was restored
   SHA-256-identical and the suite returned to green (drill record
   in `tests/README.md`).
2. **[L3]** Audit tamper: mutating a stored audit entry in place
   makes `verify_chain()` report failure at exactly that entry's
   index, and editing one line of the JSONL file is detected after
   reload — proving the chain catches the tampering defect class
   rather than merely existing (in `tests/test_audit_chain.py`).

## Coverage statement (for this build)

- Forks spec'd: **2 / 2**, each with evidenced claims (6 total, after
  1 documented wording-artifact correction; 6 near-misses recorded).
- Core implemented: **12 / 12** functions, at the High baseline; 6
  tier uplifts implemented (hash-chained audit, fail-closed audit
  writes with store-level rollback, audit query/reduction, chain
  verification endpoint, logon lockout, auditor role).

## Gaps — specified, not implemented (for the GAPS.md final batch)

Extended functions carried from the Group 12 union:
- Distributed storage engines: data lake / warehouse internals,
  database engines, replication (no sibling at either tier claims a
  storage engine as a customer-facing function; the substrate holds
  metadata and records).
- Integration runtime & connector engine: live connectors,
  transformation execution, automation runtime (Kiteworks claims
  integration as a headline function at this tier; its DLP, antivirus,
  SIEM, and directory connectors are engines of exactly this class).
- Privacy-preserving record-linkage engine: PPRL cryptography,
  universal-key matching, de-identified cohort computation;
  de-identification engines generally.
- Enterprise search indexing engine: full-text indexing at scale;
  the core's search is over registry metadata (Axon claims search
  over evidence stores at this tier; the engine behind it is this
  gap).
- Content processing engines: OCR, audio/video transcription,
  automated categorization (Axon's evidence playback / media
  handling depth rides here).
- Workflow / BPM execution engine and guided-interview engine:
  adaptive forms, interview execution, stakeholder routing; the
  core carries collection as ingestion records and approvals as
  access governance.
- Query & visualization engines: live query against source data and
  in-workflow report rendering.
- IaaS/PaaS hosting: compute, private cloud, virtual desktops,
  co-location, Authorization-as-a-Service inheritance.
- Kubernetes provisioning & cluster lifecycle engine.
- Asset inspection & capital-planning applications.
- Managed file transfer transport: protocol endpoints (SFTP/FTPS/
  SMTP/CIFS) and regulated exchange rails — **claimed outright by
  Kiteworks at this tier** (MFT is one of its three tagged claims);
  transfers in the core are ingestion-shaped records only.
- Case management depth: background investigation tracking,
  continuous vetting, adjudication workflows.
- AI/ML analytics & orchestration in bundled applications.
- Field-level / transformation lineage & provenance beyond
  ingestion records (claimed by no sibling at either tier by name;
  specified so the absence is a finding).
- Retention disposition execution: deletion/archival engines and
  NARA/FOIA production; the core schedules and reports due state
  only.

This group's own verticals (one sibling each):
- Axon: digital-evidence management depth (evidence playback,
  redaction, sharing/disclosure workflows), device fleet control
  (body-worn / in-car cameras, TASER devices, interview rooms),
  real-time operations / situational-awareness platform
  (Axon Respond), and records & report-writing automation
  (Axon Records).
- Kiteworks: secure file transfer & sharing platform depth (web /
  email / SFTP / MFT / API channels as working transports), Secure
  Data Forms, possessionless editing (SafeEDIT: streaming,
  rendering, versioning, revocation), DLP / CDR / antivirus
  engines, customer-managed encryption keys and key management,
  SIEM forwarding.

Platform layer (gap-listed, never implied closed): MFA /
authenticator management (IA-2(1)/(2), IA-5); FIPS-validated
cryptography (SC-13); encryption at rest (SC-28); audit retention
enforcement (AU-11); session lock / termination (AC-11/AC-12);
encryption in transit is TLS only when a certificate is configured;
multi-tenancy (the build is a single-tenant reference deployment —
Kiteworks' dedicated-VPC-per-customer shape is its deployment
substrate, recorded in the artifact log); demo identities are
hooks, not an IdP — IA-2 stays with the embedding organization.
