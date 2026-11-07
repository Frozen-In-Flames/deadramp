# Final GAPS batch — Group 28, Data Management L3-adjacent

Unit: the 14 entries in GAPS.md under "Group 28 — Data Management
L3-adjacent (2 forks)" (7 `build-extension`, 7 `stub-engine` in
`../../gaps-batch/inventory.json`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07), with **one
re-judgment** (retention disposition execution, grounds below —
the same adjudication the Group 12 batch unit reached for the
identical entry one tier down). The section's two prose paragraphs
(the group's own verticals; the High baseline platform-layer gaps)
are not among the 14 entries; they are named in the long-tail
enumeration only so nothing is read as silently absorbing them.

All extension code is in one new module,
`src/datamgmt/extensions.py` (`DataMgmtExtensions`, wrapping the
core `DataMgmtStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified; `store.py` still
`7e4544a4…`, the shipped hash). Full suite: 239 tests before,
**293 tests after, OK** (54 new in `tests/test_gaps_batch.py`),
including the fresh mutation-verified negative control recorded
in `tests/README.md`.

The family forms follow the Group 12 (Data Management L2) batch
unit's established precedent (`../data-management-l2/BATCH.md`)
family by family, adapted to this tier's core — the L2 substrate
carried up with the High-baseline uplifts. The adaptations are
in the extension layer only; no core module changed:

- **Fail closed (AU-5).** The core store wraps every mutation in
  the `_atomic` snapshot guard so an operation whose audit write
  fails does not proceed. The extension holds its own records, so
  `_create` applies the same posture: if the audit write raises
  `AuditWriteError`, the record insertion and its id are rolled
  back before the error propagates. A test pins it end to end
  (broken JSONL log → `AuditWriteError`, no record, `stg-1` not
  consumed, retry after repair takes `stg-1`, chain verifies).
- **Hash-chained audit (AU-9).** Extension entries (`ext_*`,
  `:denied`) are ordinary entries on the core's hash-chained log;
  a test pins that they carry `seq`/`prev_hash`/`hash` and that
  `verify_chain()` verifies over them.
- **Auditor role (AC-5).** This tier's fourth role holds
  `audit_read` only, so it holds no permission anywhere on the
  extension surface — every extension read/write maps onto an
  operational core action — exactly as at the core store layer.
  Tests pin the auditor denied on a write, on reads, and on a
  case decision, each denial audited.

Cross-cutting, per the group's doctrines: RBAC is enforced through
the core `datamgmt.access` matrix — the extension maps each
operation onto an existing core action (the core action set is
fixed) and checks it before any state change or id allocation;
denied attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`; all parties, assets, systems, and evidence are
opaque `*_ref` strings, and no record shape can hold an identifier
value or record payload rows; derived values (storage views,
linkage rollups, inspection rollups, capital totals, lineage
views) are computed at read and never stored; money is integer
cents with booleans/floats rejected at the boundary; provenance
stays bounded to ingestion granularity, with the boundary labeled
in the lineage view itself.

## Re-judgment (DECISION.md qualification 1)

**Retention disposition execution** — drafted `build-extension`;
**re-judged to a labeled reference implementation** (closure
token `reference`).

Grounds, on a close reading of this group's own spec and the
platform decision (the same grounds the Group 12 unit recorded
for the identical entry, restated against this group's text):

1. `PLATFORM-LAYER.md` decision 4 places retention-period
   enforcement and eventual disposition with the embedding
   organization's records schedule, executed at the deployment
   layer. `UNION-SPEC.md` states the same bound for this group
   twice: Core function 8 is "schedules and reports; it does not
   execute disposition," and the retention gap itself is defined
   against that bound ("the core schedules and reports due state
   only").
2. The build's audit log is append-only and — at this tier —
   hash-chained with no deletion API, and the substrate holds
   registry metadata and records, not the underlying content
   stores (at this tier: not Axon's evidence stores and not
   Kiteworks' content enclave). There is nothing in this build an
   execution engine could honestly delete or archive, and a
   method that reported deletion without deleting would be a
   false claim, not an extension.
3. What honestly lands in-substrate is the decision layer the
   core stops one step short of: disposition **decision** records
   whose eligibility is derived at record time from the core's
   own retention schedules and `retention_due` evaluation (legal
   hold and in-window datasets record `eligible: False`), plus
   **execution reference** records for approved decisions that
   hand execution to the embedding organization's records
   schedule. Every record carries `reference_stub: True` and
   `disposition_executed: False` / `executed: False`, and a test
   pins that after an approved, eligible decision the dataset
   and its policy are still present and untouched.

Precedent: the Group 12 batch unit adjudicated the identical
entry to this same disposition on these grounds (its BATCH.md),
and the Accounting units built retention as decision records with
derived eligibility in the same spirit. The parent closes this
entry with token `reference`.

No other entry required re-judgment: each remaining family fits
the L2 form at this tier without breaking a founding invariant.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `datamgmt/extensions.py`) |
|---|---|---|
| Distributed storage engines | built | `register_storage_volume` (`stg-`, engine kind enum, reported capacity/replicas), `storage_summary` — volume counts by engine, reported-capacity and replica totals, and core ingestion totals derived at read; record carries `state: registered` and the summary `engine_executed: False`. Records about storage, matching the spec's named absence (no sibling at either tier claims a storage engine; the substrate holds metadata) |
| Integration runtime & connector engine | reference (stub-engine) | `register_connector` (`con-`, opaque `system_ref`, direction), `record_connector_run` (`crn-`, outcome stored verbatim as the runtime's report) — every record carries `reference_stub: True`; runs also `executed_here: False`. At this tier the family is claimed outright by Kiteworks (its DLP, antivirus, SIEM, and directory connectors are engines of this class); the records form does not absorb that claim — no connector runs |
| PPRL record-linkage & de-identification engines | built | `record_linkage_report` (`lnk-`, a reported pair of **opaque refs**, optional core-ingestion binding validated against the dataset; `match_computed_here: False` — no identifier value is accepted and no matching runs, so no PPRL cryptography and no universal-key matching is claimed), `linkage_summary` (counts/distinct refs by method, derived), `declare_deidentification` (`dei-`, method declaration with `applied_here: False`, `records_transformed: 0` — a governance record, never a transformation) |
| Enterprise search indexing engine | reference (stub-engine) | `define_search_index` (`idx-`), `record_index_snapshot` (`isn-`, reported document count, `indexed_here: False`) — `reference_stub: True` throughout; the core's metadata search remains the only search that runs (pinned by test). Axon claims search over evidence stores at this tier; the engine behind it is this entry, and it is not built |
| Content processing engines (OCR / transcription / categorization) | reference (stub-engine) | `register_processing_job` (`prc-`, kind enum, optional ingestion binding; `outputs_held: False`), `record_processing_output` (`pro-`, opaque `output_ref` only, `content_held: False`) — `reference_stub: True` throughout |
| Workflow / BPM & guided-interview engines | reference (stub-engine) | `define_workflow` (`wfl-`, step labels held as data, `executed: False` — definitions only, per the house registry doctrine), `define_guided_interview` (`giv-`, questions verbatim as data, optional workflow binding) — `reference_stub: True` throughout |
| Query & visualization engines | built | `define_query` (`qry-`, registered deterministic derivation specs: count_records / count_by_field / sum_field / field_histogram, with optional scalar filter), `run_query` (`qrs-`, evaluates the spec over a supplied batch and records the run as an event — the core quality-check shape; the build holds no live store and reaches into none), `define_visualization` (`viz-`, `definition_only: True`), `render_visualization` — view derived at read from stored run records, `executes_query: False` |
| IaaS / PaaS hosting; Kubernetes provisioning engine | reference (stub-engine) | One GAPS entry at this tier, two record surfaces as at L2: `record_hosting` (`hst-`, kind enum incl. virtual_desktop and analytics_service, `hosted_here: False`) and `register_cluster` (`clu-`, opaque `blueprint_ref`, `provisioned_here: False`) with `record_cluster_lifecycle` (`clc-`, lifecycle events stored verbatim as reported, `performed_here: False`) — `reference_stub: True` throughout; the build remains a single-tenant reference deployment and provisions nothing |
| Asset inspection & capital-planning apps | built | `record_inspection` (`insp-`, opaque `asset_ref`, outcome enum, integer finding count), `inspection_summary` (counts by outcome, distinct assets, total findings — derived), `create_capital_plan` (`cap-`), `add_capital_item` (`cit-`, integer cents, year within horizon), `capital_plan_view` — totals and per-year sums derived at read; the stored plan record carries no total (pinned by test) |
| Managed file transfer transport (claimed outright by one sibling at this tier; transfers in the core are ingestion-shaped records) | reference (stub-engine) | `record_file_transfer` (`trf-`, ingestion-shaped: dataset + core source, protocol enum, count/checksum) — carries `reference_transport: True` and `moved_here: False`; no file moves, and Kiteworks' outright MFT claim is recorded as the claim it is, not absorbed — the transport itself (SFTP/FTPS/SMTP/CIFS endpoints, exchange rails) is not in this build |
| Case management depth | built | `open_case` (`case-`, opaque `subject_ref`, kind enum), `record_case_evidence` (`cev-`, opaque refs only, closed once decided), `decide_case` (`cde-`) under the new separation-of-duties seam `_check_case_decider_not_opener` — the decider may never be the opener (AC-5), mirroring the core's signature guard; the seam is the batch's fresh negative control |
| AI/ML analytics in bundled apps | reference (stub-engine) | `register_model` (`mdl-`, `method: recorded_declaration_only`, `trained_here: False`, `inference_here: False`), `record_orchestration` (`orc-`, `executed_here: False`) — `reference_stub: True` throughout; no model is declared to run |
| Field-level / transformation lineage (provenance stays bounded to ingestion granularity) | built | `record_transformation_step` (`stp-`, declared step kind + field bound to a core ingestion of the same dataset; `executed_here: False` — steps are declarations about a pipeline, never executed transformations), `field_lineage` — steps for a (dataset, field) joined at read with the core provenance totals, both granularities labeled in the view (`granularity: field_level_declared_steps`, `core_provenance_granularity: ingestion`) |
| Retention disposition execution | **reference (re-judged from build-extension — grounds above)** | `record_disposition_decision` (`ddc-`, eligibility/age/legal-hold derived from the core policy + `retention_due` at record time; `reference_stub: True`, `disposition_executed: False`), `record_disposition_execution_reference` (`dex-`, approved decisions only; `executed: False`) |

## Long-tail enumeration

Against the 19 families of `UNION-SPEC.md`'s function ranking and
the 15 items of its gap list:

| Spec family | Where it lands |
|---|---|
| Integration, connectivity & data exchange | Core (sources/ingestion/export/API) + the connector stub entry. At this tier Kiteworks claims the family outright; the engines (DLP/antivirus/SIEM/directory connectors) remain the stub entry, not the core |
| Dataset, records & repository registry | Core (dataset registry; Axon's claim) — no extension needed, none built |
| Catalog search & discovery | Core (metadata search; Axon's claim) + the search-index stub entry |
| Ingestion & data collection | Core (ingestion records; Axon's claim) + processing-job and file-transfer record surfaces |
| Workflow, automation, review & approvals | Approval substrate is Core (access governance); engines are the workflow stub entry |
| Query, reporting & analytics | The query & visualization entry |
| Asset, cluster & infrastructure lifecycle management | Asset half: the inspection & capital-planning entry. Cluster half: the Kubernetes half of the hosting stub entry |
| Record linkage & matching | The PPRL entry |
| Data governance & access controls | Core — no extension needed |
| Privacy preservation & de-identification | The de-identification half of the PPRL entry |
| Retention, disposition & records lifecycle | Core (schedules + due evaluation; Kiteworks' claim) + the re-judged retention entry |
| Content processing (OCR, transcription, categorization) | The content-processing stub entry |
| Data quality, accuracy & completeness validation | Core — no extension needed |
| Guided data collection (forms & intelligent interviews) | The guided-interview half of the workflow stub entry; submissions remain Core ingestion-shaped records |
| API / programmatic access | Core (REST API) — no extension needed |
| Cloud platform hosting (compute, storage, private cloud) | The hosting half of the hosting stub entry (Kiteworks' VPC raw hit was corrected out as substrate at spec time and stays out) |
| Case management & adjudication | The case entry |
| Managed file transfer | The file-transfer entry (Kiteworks, claimed outright at this tier) |
| AI/ML analysis & orchestration | The AI/ML stub entry |
| Distributed storage engines (gap list; the ranking's named absence) | The storage entry |
| Field-level / transformation lineage (gap list; claimed by no sibling at either tier) | The lineage entry |

**Named as NOT covered by this unit** (so the enumeration closes
only what it lists):

- **Transformation execution.** The lineage entry records declared
  steps; no engine in this unit transforms data. That is the
  entry's stated boundary, not a fifteenth entry.
- **This group's own verticals** (the GAPS.md section's prose
  paragraph, not among the 14 entries): Axon's digital-evidence
  management depth, device fleet control, real-time operations
  platform, and records/report-writing automation; Kiteworks'
  secure transfer & sharing platform depth, Secure Data Forms,
  possessionless editing (SafeEDIT), DLP / CDR / antivirus
  engines, customer-managed keys, and SIEM forwarding. Two of
  these ride families this unit does touch — the DLP/SIEM
  connectors ride the integration family and the transfer depth
  rides the MFT family — but the vertical engines themselves are
  not built here and no entry in this unit closes them.
- **The section's High baseline platform-layer paragraph** (MFA /
  authenticator management IA-2(1)/(2) & IA-5, FIPS-validated
  cryptography SC-13, encryption at rest SC-28, audit retention
  AU-11, session lock / termination AC-11/AC-12) — not among the
  14 entries; it stands on `PLATFORM-LAYER.md`, and the hosting
  stub entry does not absorb it. One sibling's FIPS 140-3 and
  MFA/PIV/CAC/TOTP product claims are that sibling's, recorded
  in the spec, and do not transfer.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
