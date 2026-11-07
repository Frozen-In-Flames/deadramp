# Final GAPS batch — Singleton 53, Research L2

Date: 2026-11-07. This section of `../../GAPS.md` listed 10 open
entries (inventory idx 521–530); all 10 are closed by this unit
under the decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`.

What landed: one new module, `src/research/extensions.py`
(`ResearchExtensions`, wrapping the core `ResearchStore`; all
seven core modules byte-identical, SHA-256 verified against the
pre-build sums — store.py still `ff43a9ac…`, the shipped hash),
and `tests/test_gaps_batch.py` (34 tests). Full suite: **97 → 131
tests**, all passing.

The founding discipline binds every shape built here: the commons
is a registry of dataset records and counts. Records carry
metadata and opaque caller-supplied references only — no shape
has a field for research subject data, a dataset payload, a query
text, a cohort member, or a score. That is pinned by exact
key-set assertions per record type, by `TypeError` on any
unexpected keyword argument, and by a recursive forbidden-key
scan over every extension record, view, and summary. Every
"engine" below is its in-substrate form: definition and outcome
records over the group's OWN records (core records and extension
records), plus deterministic derivations at read — nothing here
holds, moves, transforms, queries, or harmonizes actual data.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 521 | Data commons runtime engine | built | Runtime *configuration* records (`rt-`; unique `config_ref` per commons; profile label + parameter references held as data) over core commons records. `runtime_started_here: False` on every record; the parameter count is derived at read in `runtime_config_view` and never stored. No runtime is started, configured, or operated here. |
| 522 | Data ingestion / ETL engine | built | Pipeline *definition* records (`pl-`; bound to a core dataset in the same commons; source reference and transform-step references held as names; `data_held_here: False`) plus run records (`run-`; reported-* state vocabulary; counts stored exactly as reported; `ingested_here: False`). A test pins that recording a run leaves the core dataset record byte-identical. `ingestion_summary` is a deterministic counts derivation (`deterministic_counts`). |
| 523 | Data harmonization engine | built | Mapping *definition* records (`map-`; source/target field references held as names, duplicates refused; `harmonized_here: False`) plus conformance outcome records (`cfm-`; reported-* outcome vocabulary, stored verbatim as reported). Field counts are derived at read in `mapping_view`; `harmonization_summary` is `deterministic_counts` over the held records. Nothing is harmonized here. |
| 524 | Indexing & metadata catalog engines beyond the registry | reference | Labeled reference records (`idx-`): `reference_stub: True`, state `recorded_reference_only`, `index_built_here: False`. A test pins that recording an index reference leaves the core registry's literal substring search results unchanged — no index is built and no search behavior is replaced. |
| 525 | Query & analysis workspace engines | built | Query *definition* records (`qry-`) bound to a core workspace record, held as text-free structure: field references and operator names as data, `executed_here: False`. No parameter accepts query text (pinned by `TypeError` on a `query_text` keyword). Result records (`qrs-`) hold counts exactly as reported (`computed_here: False`); structure counts are derived at read in `query_view`. No query ever executes here. |
| 526 | Cohort builder / cohort discovery engine | built | Cohort *definition* records (`coh-`) over a core dataset: criteria references held as names; `members_computed_here: False`. Membership records (`cmr-`) hold counts exactly as reported. No shape has a field that could hold a subject reference (exact key set pinned; `TypeError` on a `subject_refs` keyword). `cohort_summary` totals the reported counts (`deterministic_counts`). No member is computed, discovered, or named here. |
| 527 | Cross-commons federation / data mesh networking | built | Peer-commons records (`per-`; opaque peer reference + label, unique per commons; `connected_here: False`), exchange request records (`exr-`; core dataset reference + purpose; `reference_transport: True`), and exchange outcome records (`exo-`; reported-* vocabulary stored verbatim; `data_moved_here: False`, `reference_transport: True`). `federation_summary` is `deterministic_counts`. Nothing connects or meshes here. |
| 528 | Data delivery / transfer engine for sharing | built | Delivery records (`dlv-`) over core dataset references with an optional core grant reference (validated to name a grant for the same dataset in the same commons), plus append-only delivery state records (`dls-`; reported-* labels). The current state is derived at read by the single seam `_current_delivery_label` (latest recorded label) and never stored — the stored delivery record carries no state key. `data_moved_here: False` on both shapes; no data moves here. |
| 529 | Access enforcement on data delivery (grants are records that confer nothing; no data moves in this build) | built | Enforcement decision records (`enf-`; reported-* decision vocabulary recorded as reported by the delivery layer's own enforcement point; `conferred_here: False`, `enforced_here: False`) plus `delivery_access_view`, which derives the linked core grant's status through the CORE store's own `_derive_grant_status` (via `get_grant`) at the read clock — scheduled/active/expired all verified against the canonical fixture grant. The founding line is pinned behaviorally in both directions: minting a core grant leaves a delivery record, its state records, and its view byte-identical, and recording an enforcement decision leaves the core grant record byte-identical and the delivery's derived state unchanged. |
| 530 | Identity provider / identity management service | reference | Labeled reference records (`idr-`): `reference_stub: True`, state `recorded_reference_only`, `identity_provider: False` — per PLATFORM-LAYER.md decision 1, identity proofing, authenticator management, and any identity-provider service stay with the embedding organization; the record names the external provider in use, and the core's demo identities remain hooks, not an IdP. |

Closure tokens: 8 entries close as `built` (521, 522, 523, 525,
526, 527, 528, 529) and 2 as `reference` (524, 530).

## Re-judgments

None. Every build-extension entry was carried in the records form
the brief prescribes under the founding registry discipline, and
both stub-engine entries shipped as their drafted labeled
reference implementations. The three entries nearest the line are
stated plainly rather than re-judged:

- **Access enforcement (529)** is built as decision *records*
  plus a derived view over the core grant's own derived status —
  not as an enforcement point: this build gates records, confers
  nothing, and enforces nothing on any actual data read, exactly
  as the entry's own parenthetical bounds it.
- **Cohort building (526)** is built as cohort *definitions* with
  reported membership counts — not as discovery: no criteria are
  ever evaluated against anything here, because the substrate
  holds no subject data to evaluate them against.
- **Query & analysis (525)** is built as query *definitions* —
  not as an engine: the description names no analysis method
  (UNION-SPEC records the same bound for the core), and a
  definition held as data is the records form the activity
  presupposes.

## Negative control

Fresh, for the new code: the delivery current-state derivation
(`ResearchExtensions._current_delivery_label` — latest recorded
label wins). In-suite three-leg control in
`tests/test_gaps_batch.py`
(`TestDeliveryDerivationNegativeControl`, mutant subclass reads
the earliest recorded label), plus a live drill on the real
file: the seam was patched to `return states[0]["state_label"]`,
the full suite ran **131 tests with exactly 2 failures** (the
derivation-dependent set: the deliveries current-state test and
the control's canonical arm — the mutant-agreement legs and the
single-state delivery tests pass under both by construction),
then the file was restored from
`scratch/extensions.py.premutation` and verified SHA-256
identical (`9c82de73…`); suite green again. Full record in
`tests/README.md`.

## Core integrity

No core module was modified: `src/research/*.py` SHA-256 sums for
all seven pre-existing modules match the pre-build accounting
exactly (store.py `ff43a9ac…`, the shipped hash recorded in
`scratch/store.py.sha256`). The extension is store-level only (no
HTTP routes), matching the sibling batch units' pattern — the
core `service.py` is byte-identical and untouched.
