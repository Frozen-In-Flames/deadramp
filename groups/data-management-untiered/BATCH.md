# Final GAPS batch — Untiered Set 5, Data Management (8 forks, tier null)

Unit: the 10 entries in GAPS.md under "Untiered Set 5 — Data
Management (8 forks, tier null)" (idx 786–795 in
`../../gaps-batch/inventory.json`; 6 `build-extension`,
4 `stub-engine`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No entry
is re-judged.** Two components inside entries follow adjudicated
forms from the sibling Data Management batch units, with the
grounds stated where they land (disposition execution, inside
the archive/production entry; query runs, inside the
query & visualization entry).

All extension code is in one new module,
`src/datamgmt/extensions.py` (`DataMgmtExtensions`, wrapping the
core `DataMgmtStore`); every existing core module is
byte-identical to its pre-batch state (SHA-256 verified against
the accounting in this group's README; `store.py` still
`dc35677c…`). Full suite: 202 tests before, **241 tests after,
OK** (39 new in `tests/test_gaps_batch.py`), including the fresh
mutation-verified negative control recorded in
`tests/README.md`.

**Tier discipline binds the extension surface exactly as it
binds the core.** Nothing here asserts or records a tier, a
control baseline, or an equivalence: no record shape carries a
tier-shaped key, and a test scans every extension record and
derived view recursively for tier/baseline/equivalence keys (and
for floats and numeric lists, a vector value being a list of
numbers). The forks' documented control claims remain where
`UNION-SPEC.md` put them — the forks' claims about themselves,
recorded in the spec; the ABAC entry below builds the records
form of a function one fork *describes* at that prose tier, and
claims no control attainment for it.

Cross-cutting, per the group's doctrines: RBAC is enforced
through the core `datamgmt.access` matrix — the extension maps
each operation onto an existing core action (the core action set
is fixed) and checks it before any state change or id
allocation; denied attempts are recorded on the core audit log
as `ext_<action>:denied` and every successful mutation as
`ext_<action>`; all parties, systems, and outputs are opaque
`*_ref` strings or core record ids, and no record shape can
hold a payload, an identifier value, a vector value, or
extracted content; counts describing an external engine's work
are stored as reported, never computed here; derived values
(warehouse rollups, graph degrees, ABAC decision outcomes,
visualization series) are computed at read and never stored.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `datamgmt/extensions.py`) |
|---|---|---|
| AI/ML engines (six claimants in this set; the build computes nothing learned) | reference (stub-engine) | `register_model` (`mdl-`, `method: recorded_declaration_only`, `trained_here: False`, `inference_here: False`), `record_model_run` (`mrun-`, outcome stored verbatim as the platform's report, output held as an opaque `output_ref` only) — `reference_stub: True` throughout; no model is declared to run |
| Vector database & embedding index engine | built | `define_vector_collection` (`vcol-`, a definition: name, optional core dataset binding, reported dimension, metric label; `definition_only: True`, `embeddings_computed_here: False`), `record_embedding_job` (`emb-`, document/embedding counts stored as reported). No vector value exists in any shape — there is no parameter that could accept one (pinned by TypeError tests and the recursive shape scan) |
| Document processing engines (OCR, classification, deduplication) | reference (stub-engine) | `register_processing_job` (`prc-`, kind enum ocr / classification / deduplication — this set's kinds, per Wisedocs' described functions; optional core-ingestion binding validated against the dataset; `processed_here: False`, `outputs_held: False`), `record_processing_output` (`pro-`, opaque `output_ref` + reported count only, `content_held: False`) — `reference_stub: True` throughout; no extracted-text field exists (pinned by exact key set and a TypeError test) |
| Petabyte-scale warehouse & analytics engine | built | `register_warehouse` (`wrh-`, configuration record; the scale label is recorded verbatim as `scale_label_reported` — the platform's own label, never a capacity claim by this build; `data_held_here: False`), `record_warehouse_query_run` (`wqr-`, row counts as reported, `executed_here: False`), `warehouse_summary` — run count and reported-row total derived at read; the stored configuration record carries no totals (pinned by test) |
| Enterprise architecture graph platform | built | `register_graph_node` (`gnod-`, opaque `node_ref` unique in the registry, kind label, optional dataset binding), `record_graph_edge` (`gedg-`, both endpoints must be registered nodes), `graph_node_view` — in/out/total degree derived at read from the edge records (the Research untiered precedent); the stored node record carries no degree (pinned by exact key set) |
| Policy enforcement plane & ABAC engine | built | `define_abac_policy` (`abac-`, definition held as data: core dataset binding, required attribute *names*, effect label; `definition_only: True`), `record_subject_attributes` (`suba-`, attribute names present for an opaque `subject_ref` — presence only, no value is accepted), `record_abac_decision` (`abdec-`, binds policy + subject; the outcome is **not** stored), `abac_decision_view` — `matched` / `missing_attributes` derived at read by the seam `_attributes_satisfy` (deterministic attribute-presence match, the personalization precedent's form; the batch's fresh negative control). Enforcement is not performed (`enforced_here: False` on every record and view), and a test pins that recording and viewing a decision leaves the core's datasets, access requests, and grants byte-for-byte unchanged |
| Managed file transfer transport | reference (stub-engine) | `record_file_transfer` (`trf-`, ingestion-shaped: core dataset + core source, protocol enum, count/checksum) — carries `reference_transport: True`, `moved_here: False`, `transferred_here: False`; no file moves |
| Archive, eDiscovery & FOIA production, including disposition execution (the build records schedules; it executes nothing) | built (production records built; the disposition-execution component ships in the sibling units' adjudicated reference form — see note 1) | `record_production` (`prd-`, kind enum archive / ediscovery / foia, counts as reported + checksum reference, `content_held: False`, `executed_here: False`); `record_disposition_decision` (`ddc-`, eligibility/age/legal-hold derived from the core policy + `retention_due` at record time; `reference_stub: True`, `disposition_executed: False`), `record_disposition_execution_reference` (`dex-`, approved decisions only; `executed: False`) |
| Search indexing engine | reference (stub-engine) | `define_search_index` (`idx-`, `index_built_here: False`), `record_index_snapshot` (`isn-`, reported document count, `indexed_here: False`, `index_built_here: False`) — `reference_stub: True` throughout; the core's literal metadata search remains the only search that runs (pinned by a before/after equality test) |
| Query & visualization engines | built (definitions + reported runs; see note 2) | `define_query` (`qry-`, a definition in text-free structure: kind enum count_records / count_by_field / sum_field / field_histogram, a field *name*, an optional scalar filter; `definition_only: True`, `executed_here: False`), `record_query_run` (`qrs-`, scanned/matched counts stored as reported, `executed_here: False`), `define_visualization` (`viz-`, `rendered_here: False`), `visualization_view` — series derived at read from stored run reports, `executes_query: False`. No parameter can accept query text or a record batch (pinned by TypeError tests) |

## Adjudication notes

**1. Disposition execution, inside the archive/production
entry.** The Data Management L2 and L3-adjacent batch units each
re-judged a *standalone* entry naming disposition execution
alone to a labeled reference implementation, on the grounds that
`PLATFORM-LAYER.md` decision 4 places disposition with the
embedding organization's records schedule and this substrate
holds nothing an execution engine could honestly delete or
archive. Those grounds bind the disposition-execution
*component* here identically, and the component ships in
exactly that adjudicated form (decision records and execution
reference records, every one labeled `reference_stub: True`,
nothing executed). The entry as a whole is **not** re-judged:
its own text bounds it ("the build records schedules; it
executes nothing"), and its center of mass is the production
platform — archive, eDiscovery, and FOIA production records —
which is built above. The parent may close the entry `built`
for the production platform with the execution component
labeled reference in-record, as recorded here.

**2. Query runs.** The L2 unit's query surface evaluated
registered deterministic derivations over a batch supplied in
the call (the core quality-check shape). This unit ships the
stricter records form — definitions held as data plus run
records whose counts are stored as reported — on two grounds:
this set's own spec places query & visualization *engines* in
Extended with a single claimant and describes the core's share
as "records/provenance" substrate only; and no fork in this set
describes a derivation this build could evaluate without
inventing one. Nothing is executed here, and the definition
structure (kind / field name / scalar filter) is the same
text-free structure the L2 form registered.

**3. ABAC claim posture.** `data_governance` has **0 claimants**
in this set under the verbatim taxonomy (the union spec's
headline named absence); Immuta's ABAC substance is documented
at the prose tier in the spec's Documented control claims. The
extension builds the records form of that described function —
policy definitions, recorded attribute presence, derived
decision outcomes — and asserts no taxonomy claim and no
control attainment for it, exactly as the spec records the
fork's claim as the fork's. The core's own access governance
(requests, decisions never by the requester, grants) is a
separate core function and is untouched; a test pins the
extension's decisions change none of it.

## Long-tail enumeration

Against the 10 items of this set's gap list in `UNION-SPEC.md`
(each maps to the entry of the same name in the table above)
and the standing category gaps the spec carries:

**Named as NOT covered by this unit** (so nothing is read as
silently absorbed):

- **Standing category gaps with no claimant in this set**,
  carried from the founding spec unchanged and untouched here:
  integration runtime & connector engine; privacy-preserving
  record-linkage engine and de-identification engines (the L2
  unit built their records forms under its own section; this
  set's section registers no such entry); workflow / BPM
  execution engine and guided-interview engine; IaaS/PaaS
  hosting; case management depth; asset & cluster lifecycle
  engines; field-level / transformation lineage beyond
  ingestion records.
- **The section's platform-layer paragraph** (encryption at
  rest — Pinecone and ZL document it for themselves; the build
  claims none — TLS only when a certificate is configured;
  multi-tenancy; demo identities / IA-2) — not among the 10
  entries; it stands on `../../PLATFORM-LAYER.md`, and no
  entry here absorbs it. Per decisions 2–3, the forks'
  encryption postures are the forks' own and do not transfer.
- **Group 12 (Data Management L2) and Group 28 (Data
  Management L3-adjacent)** registered this category's extended
  families under their own sections and closed them in their
  own batch units. Those entries belong to those units; the
  forms here mirror them where this set's spec supports them,
  and nothing here re-closes them.

Left unresolved: nothing in this unit. HTTP exposure of the
extension surface was out of scope for the batch pattern
(extensions land in `src/` with tests); the service layer is
untouched.
