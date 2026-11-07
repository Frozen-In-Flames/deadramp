# Final GAPS batch — Group 12, Data Management L2

Unit: the 16 entries in GAPS.md under "Group 12 — Data Management
L2 (8 forks)" (8 `build-extension`, 8 `stub-engine` in
`../../gaps-batch/inventory.json`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07), with **one
re-judgment** (retention disposition execution, grounds below).
The section's "Platform-layer" paragraph (encryption at rest,
TLS-when-configured, multi-tenancy, demo identities/IA-2) is not
part of the 16 entries; it stands closed by
`../../PLATFORM-LAYER.md` and is named in the long-tail enumeration
only so the catch-all entry is not read as absorbing it.

All extension code is in one new module,
`src/datamgmt/extensions.py` (`DataMgmtExtensions`, wrapping the
core `DataMgmtStore`); every existing core module is byte-identical
to its pre-batch state (SHA-256 verified; `store.py` still
`dc35677c…`). Full suite: 208 tests before, **257 tests after, OK**
(49 new in `tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines: RBAC is enforced through
the core `datamgmt.access` matrix — the extension maps each
operation onto an existing core action (the core action set is
fixed) and checks it before any state change or id allocation;
denied attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`; all parties, assets, systems, and evidence are
opaque `*_ref` strings, and no record shape can hold an identifier
value or record payload rows; derived values (storage views,
linkage rollups, inspection rollups, capital totals, lineage views)
are computed at read and never stored; money is integer cents with
booleans/floats rejected at the boundary.

## Re-judgment (DECISION.md qualification 1)

**Retention disposition execution (deletion / archival engines,
NARA / FOIA production; the core schedules and reports due state
only)** — drafted `build-extension`; **re-judged to a labeled
reference implementation** (closure token `reference`).

Grounds, on a close reading of the owning group's spec and the
platform decision:

1. `PLATFORM-LAYER.md` decision 4 places retention-period
   enforcement and eventual disposition with the embedding
   organization's records schedule, executed at the deployment
   layer. `UNION-SPEC.md` states the same bound twice: Core
   function 8 is "schedules and reports; it does not execute
   disposition," and the retention gap itself is defined against
   that bound.
2. The build's audit log is append-only with no deletion API, and
   the substrate holds registry metadata and records, not the
   underlying content stores — there is nothing in this build an
   execution engine could honestly delete or archive, and a method
   that reported deletion without deleting would be a false claim,
   not an extension.
3. What honestly lands in-substrate is the decision layer the core
   stops one step short of: disposition **decision** records whose
   eligibility is derived at record time from the core's own
   retention schedules and `retention_due` evaluation (legal hold
   and in-window datasets record `eligible: False`), plus
   **execution reference** records for approved decisions that hand
   execution to the embedding organization's records schedule.
   Every record carries `reference_stub: True` and
   `disposition_executed: False` / `executed: False`, and a test
   pins that after an approved, eligible decision the dataset and
   its policy are still present and untouched.

This follows the batch's own precedent: the Accounting units built
retention as "the retention record and the derived eligibility
check; disposition itself stays with the embedding organization's
records schedule per PLATFORM-LAYER.md" — here the entry's text
names *execution* itself, so the honest closure token is
`reference`, not `built`.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `datamgmt/extensions.py`) |
|---|---|---|
| Distributed storage engines (data lake / warehouse internals, database engines, replication) | built | `register_storage_volume` (`stg-`, engine kind enum, reported capacity/replicas), `storage_summary` — volume counts by engine, reported-capacity and replica totals, and core ingestion totals derived at read; record carries `state: registered` and the summary `engine_executed: False`. Records about storage, matching the spec's named absence (no sibling claims a storage engine; the substrate holds metadata) |
| Integration runtime & connector engine (iPaaS execution) | reference (stub-engine) | `register_connector` (`con-`, opaque `system_ref`, direction), `record_connector_run` (`crn-`, outcome stored verbatim as the runtime's report) — every record carries `reference_stub: True`; runs also `executed_here: False` |
| PPRL record-linkage engine & de-identification engines | built | `record_linkage_report` (`lnk-`, a reported pair of **opaque refs**, optional core-ingestion binding validated against the dataset; `match_computed_here: False` — no identifier value is accepted and no matching runs), `linkage_summary` (counts/distinct refs by method, derived), `declare_deidentification` (`dei-`, method declaration with `applied_here: False`, `records_transformed: 0` — a governance record, never a transformation) |
| Enterprise search indexing engine (the core searches registry metadata) | reference (stub-engine) | `define_search_index` (`idx-`), `record_index_snapshot` (`isn-`, reported document count, `indexed_here: False`) — `reference_stub: True` throughout; the core's metadata search remains the only search that runs (pinned by test) |
| Content processing engines (OCR, transcription, categorization) | reference (stub-engine) | `register_processing_job` (`prc-`, kind enum, optional ingestion binding; `outputs_held: False`), `record_processing_output` (`pro-`, opaque `output_ref` only, `content_held: False`) — `reference_stub: True` throughout |
| Workflow / BPM execution & guided-interview engines | reference (stub-engine) | `define_workflow` (`wfl-`, step labels held as data, `executed: False` — definitions only, per the house registry doctrine), `define_guided_interview` (`giv-`, questions verbatim as data, optional workflow binding) — `reference_stub: True` throughout |
| Query & visualization engines | built | `define_query` (`qry-`, registered deterministic derivation specs: count_records / count_by_field / sum_field / field_histogram, with optional scalar filter), `run_query` (`qrs-`, evaluates the spec over a supplied batch and records the run as an event — the core quality-check shape; the build holds no live store and reaches into none), `define_visualization` (`viz-`, `definition_only: True`), `render_visualization` — view derived at read from stored run records, `executes_query: False` |
| IaaS / PaaS hosting (compute, private cloud, DaaS, AaaS) | reference (stub-engine) | `record_hosting` (`hst-`, kind enum incl. virtual_desktop and analytics_service, `hosted_here: False`) — `reference_stub: True`; the build remains a single-tenant reference deployment |
| Kubernetes provisioning & cluster lifecycle engine | reference (stub-engine) | `register_cluster` (`clu-`, opaque `blueprint_ref`, `provisioned_here: False`), `record_cluster_lifecycle` (`clc-`, lifecycle events stored verbatim as reported, `performed_here: False`) — `reference_stub: True` throughout |
| Asset inspection & capital-planning applications | built | `record_inspection` (`insp-`, opaque `asset_ref`, outcome enum, integer finding count), `inspection_summary` (counts by outcome, distinct assets, total findings — derived), `create_capital_plan` (`cap-`), `add_capital_item` (`cit-`, integer cents, year within horizon), `capital_plan_view` — totals and per-year sums derived at read; the stored plan record carries no total (pinned by test) |
| Managed file transfer transport | reference (stub-engine) | `record_file_transfer` (`trf-`, ingestion-shaped: dataset + core source, protocol enum, count/checksum) — carries `reference_transport: True` and `moved_here: False`; no file moves |
| Case management depth (vetting / adjudication) | built | `open_case` (`case-`, opaque `subject_ref`, kind enum), `record_case_evidence` (`cev-`, opaque refs only, closed once decided), `decide_case` (`cde-`) under the new separation-of-duties seam `_check_case_decider_not_opener` — the decider may never be the opener (AC-5), mirroring the core's signature guard; the seam is the batch's fresh negative control |
| AI/ML analytics & orchestration in bundled applications | reference (stub-engine) | `register_model` (`mdl-`, `method: recorded_declaration_only`, `trained_here: False`, `inference_here: False`), `record_orchestration` (`orc-`, `executed_here: False`) — `reference_stub: True` throughout; no model is declared to run |
| Field-level / transformation lineage beyond ingestion records (the build's provenance is bounded to ingestion granularity, stated in the spec) | built | `record_transformation_step` (`stp-`, declared step kind + field bound to a core ingestion of the same dataset; `executed_here: False` — steps are declarations about a pipeline, never executed transformations), `field_lineage` — steps for a (dataset, field) joined at read with the core provenance totals, both granularities labeled in the view |
| Retention disposition execution (deletion / archival engines, NARA / FOIA production; the core schedules and reports due state only) | **reference (re-judged from build-extension — grounds above)** | `record_disposition_decision` (`ddc-`, eligibility/age/legal-hold derived from the core policy + `retention_due` at record time; `reference_stub: True`, `disposition_executed: False`), `record_disposition_execution_reference` (`dex-`, approved decisions only; `executed: False`) |
| Plus the families named in the spec's long tail | built | Enumerated family by family below; every family in the union spec's ranking and gap list maps to the core, to an entry above, or is named as not covered — nothing is silently absorbed |

## Long-tail enumeration ("Plus the families named in the spec's long tail")

Against the 19 families of `UNION-SPEC.md`'s function ranking and
the 15 items of its gap list:

| Spec family | Where it lands |
|---|---|
| Integration, connectivity & data exchange | Core (sources/ingestion/export/API) + the connector stub entry |
| Dataset, records & repository registry | Core (dataset registry) — no extension needed, none built |
| Catalog search & discovery | Core (metadata search) + the search-index stub entry |
| Ingestion & data collection | Core (ingestion records) + processing-job and file-transfer record surfaces |
| Workflow, automation, review & approvals | Approval substrate is Core (access governance); engines are the workflow stub entry |
| Query, reporting & analytics | The query & visualization entry |
| Asset, cluster & infrastructure lifecycle management | Asset half: the inspection & capital-planning entry (AMS). Cluster half: the Kubernetes stub entry (Palette VerteX) |
| Record linkage & matching | The PPRL entry |
| Data governance & access controls | Core — no extension needed |
| Privacy preservation & de-identification | The de-identification half of the PPRL entry |
| Retention, disposition & records lifecycle | Core (schedules + due evaluation) + the re-judged retention entry |
| Content processing (OCR, transcription, categorization) | The content-processing stub entry |
| Data quality, accuracy & completeness validation | Core — no extension needed |
| Guided data collection (forms & intelligent interviews) | The guided-interview half of the workflow stub entry (Intelliworx); submissions remain Core ingestion-shaped records |
| API / programmatic access | Core (REST API) — no extension needed |
| Cloud platform hosting (compute, storage, private cloud) | The hosting stub entry (GovPoint) |
| Case management & adjudication | The case entry (ABIS depth in the GovPoint bundle) |
| Managed file transfer | The file-transfer entry (Sharetru inside GovPoint) |
| AI/ML analysis & orchestration | The AI/ML stub entry (GovPoint bundle applications) |
| Distributed storage engines (gap list; the ranking's named absence) | The storage entry |
| Field-level / transformation lineage (gap list; claimed by no sibling) | The lineage entry |

**Named as NOT covered by this unit** (so the catch-all closes
only what it enumerates):

- **Transformation execution.** The lineage entry records declared
  steps; no engine in this unit transforms data. That is the
  entry's stated boundary, not a seventeenth family.
- **The section's platform-layer paragraph** (encryption at rest,
  TLS-when-configured, multi-tenancy, IdP/IA-2) — not among the 16
  entries; it stands on `PLATFORM-LAYER.md`, and the hosting stub
  entry does not absorb it.
- **Group 28 (Data Management L3-adjacent)** re-registers this
  category's extended families under its own section (GAPS.md notes
  the families are registered under Groups 12 and 28). Those
  entries belong to that unit, not this one; nothing here closes
  them.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
