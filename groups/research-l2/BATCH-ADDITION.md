# Final GAPS batch — Remainder Addition, Research L2 (+5 forks)

Date: 2026-11-07. This section of `../../GAPS.md` ("Remainder
Addition — Research L2 (+5 forks)") listed 9 open entries
(inventory idx 580–588) — the fork-excess engines of the five
remainder additions (Terra, ROSALIND, Seven Bridges, Ipsos,
Wellspring; see `ADDENDUM.md` §5). All 9 are closed by this unit
under the decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`. This is the second
batch unit in this group directory; the founding section's unit
is recorded in `BATCH.md`.

What landed: one new module, `src/research/addition.py`
(`ResearchAdditions`, a second wrapper around the core
`ResearchStore`; all seven core modules **and** the first unit's
`extensions.py` byte-identical, SHA-256 verified against the
pre-build sums — store.py still `ff43a9ac…`, the shipped hash;
extensions.py still `9c82de73…`), and
`tests/test_gaps_batch_addition.py` (32 tests). Full suite:
**131 → 163 tests**, all passing.

The founding discipline binds every shape built here, exactly as
in the core and the first batch unit: the commons is a registry
of dataset records and counts. Records carry metadata and opaque
caller-supplied references only — no shape has a field for
research subject data, a dataset payload, an analysis result
text, a sample's subject, a diagnosis, a survey response payload,
or a signature value. That is pinned by exact key-set assertions
per record type, by `TypeError` on any unexpected keyword
argument, and by a recursive forbidden-key scan over every
addition record, view, and summary. Every "engine" below is its
in-substrate form: definition and outcome records over the
group's OWN records (core records and addition records), plus
deterministic derivations at read — nothing here runs, allocates,
infers, monitors, traverses, collects, generates, signs, or
connects anything.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 580 | Interactive analysis environment & workflow execution engine (Terra) | reference | Labeled reference records: environment *definition* records (`env-`; tool references held as names, optionally bound to a core workspace; `reference_stub: True`, state `recorded_reference_only`, `provisioned_here: False`, `executed_here: False`) plus reported session outcome records (`esn-`, same labels). The tool count is derived at read in `environment_view` and never stored. No environment is provisioned and no workflow executes here. |
| 581 | Bioinformatics analysis pipeline engines (ROSALIND, Seven Bridges) | built | Pipeline *definition* records (`bpd-`; engine label and step references held as names, bound to a core dataset and optionally a core workspace in the same commons; `executed_here: False`, `data_held_here: False`) plus run-request records (`bpr-`) and run-outcome records (`bpo-`; reported-* outcome vocabulary, counts stored exactly as reported). A test pins that recording an outcome leaves the core dataset record byte-identical. `pipeline_summary` is a deterministic counts derivation (`deterministic_counts`). No analysis runs here. |
| 582 | Diagnostic monitoring & variant surveillance platform incl. BioBank sample tracking (ROSALIND) | reference | Labeled reference records: sample *tracking* records (`smp-`) keyed by an opaque caller-supplied sample reference ONLY, with a panel label — no shape has a field for a sample's subject, an identity, or a diagnosis (`TypeError` on `diagnosis` / `subject_ref` keywords, pinned). Monitoring outcome records (`mon-`) hold reported-* labels verbatim. `reference_stub: True`, `monitored_here: False` on both shapes. Nothing is monitored or diagnosed here. |
| 583 | Knowledge-graph storage & searchable library engine (ROSALIND) | reference | Labeled reference records: node records (`gnd-`) and edge records (`ged-`) as metadata references only — a node names an external resource by opaque reference; an edge names a relation label between two node references already recorded in the same commons (unknown endpoints rejected whole). `reference_stub: True`, `data_held_here: False`, `traversed_here: False` on both shapes. The records form is the whole claim, stated plainly: no graph content is held, nothing is traversed, and no graph search runs here. |
| 584 | Elastic storage & compute allocation engine (Seven Bridges) | built | Allocation *request* records (`alr-`; resource label as data and a positive integer amount — zero, negative, float, bool, and string amounts rejected whole at the boundary) plus reported allocation outcome records (`alo-`; reported-* vocabulary, amounts stored exactly as reported). `allocated_here: False` on both shapes; `allocation_summary` totals are sums of the recorded requested and reported values only (`deterministic_counts`). No scheduler runs here. |
| 585 | Multi-modal survey research platform (Ipsos) | reference | Labeled reference records: survey *definition* records (`srv-`; channel references held as names — digital, paper, and any other channel the caller names; `collected_here: False`) plus response records (`srr-`) whose counts are stored exactly as reported. `reference_stub: True` on both shapes; the channel count is derived at read in `survey_view`. No response is collected and no shape holds a response payload or a respondent reference (pinned). |
| 586 | AI analytics engine over LLMs (Ipsos) | built | Analysis *request* records (`anr-`; task label held as a name, input as an opaque reference, optionally bound to a core dataset in the same commons; `inference_here: False`) plus result records (`anx-`) holding the result as an opaque reference ONLY — no shape has a field for result text (`TypeError` on a `result_text` keyword, pinned). A test pins that recording a result leaves the core dataset record byte-identical. No inference runs here. |
| 587 | Technology transfer & IP management suite (Wellspring) | built | Disclosure records (`dsc-`; holder is an opaque reference) and agreement records (`agr-`; counterparty an opaque reference, terms a label naming an external terms record — no terms text is held), plus append-only agreement state records (`ags-`; reported-* label vocabulary stored verbatim). An agreement's current state is derived at read by the single seam `_current_agreement_label` (latest recorded label) and never stored — the stored agreement record carries no state key. A `reported_executed` label is a report that the external parties executed an agreement; `executed_here: False` on every shape. `tech_transfer_summary` recounts agreements by derived current state (`deterministic_counts`). |
| 588 | Document generation & e-signature workflow engines + external integration components (Wellspring fork excess) | reference | Labeled reference records in three families: document-generation request records (`dgr-`; template reference as a name, the generated document held as an opaque output reference only, `generated_here: False`); signing request records (`sgr-`) in the house e-signature form — document and signer named by opaque references, `signed_here: False`, and no shape has a field in which a signature value could be placed (`TypeError` on a `signature_value` keyword, pinned); and external-integration reference records (`igr-`; `connected_here: False` — Wellspring's iEdison-style components are platform-specific to the fork, per ADDENDUM.md §5, and are named here, not connected). `reference_stub: True` on every shape. |

Closure tokens: 4 entries close as `built` (581, 584, 586, 587)
and 5 as `reference` (580, 582, 583, 585, 588).

## Re-judgments

None. Every build-extension entry was carried in the records
form the brief prescribes under the founding registry
discipline, and all five stub-engine entries shipped as their
drafted labeled reference implementations. The three entries
nearest the line are stated plainly rather than re-judged:

- **Bioinformatics pipelines (581)** are built as pipeline
  *definitions* plus run requests and reported outcomes — not as
  execution: the substrate holds no data a pipeline could run
  over (dataset records are metadata + checksum), so a definition
  held as data with verbatim reported outcomes is the records
  form the activity presupposes, the same bound the first unit
  recorded for query & analysis (idx 525).
- **Knowledge-graph storage (583)** ships as node/edge
  *reference* records: the stored content is references, no graph
  engine is claimed, and `traversed_here` is False on every
  record — the stub disposition as drafted.
- **Technology transfer (587)** is built as disclosure/agreement
  records with reported state labels — not as negotiation or
  execution: a `reported_executed` state is the external
  parties' reported outcome, recorded verbatim, exactly as the
  first unit recorded enforcement decisions (idx 529).

## Negative control

Fresh, for the new code: the agreement current-state derivation
(`ResearchAdditions._current_agreement_label` — latest recorded
label wins). In-suite three-leg control in
`tests/test_gaps_batch_addition.py`
(`TestAgreementDerivationNegativeControl`, mutant subclass reads
the earliest recorded label), plus a live drill on the real
file: the seam was patched to `return states[0]["state_label"]`,
the full suite ran **163 tests with exactly 3 failures** (the
derivation-dependent set: the agreement current-state test, the
tech-transfer summary's derived-state recount, and the control's
canonical arm — the mutant-agreement legs pass under both by
construction, and no core or first-unit test failed), then the
file was restored from `scratch/addition.py.premutation` and
verified SHA-256 identical (`e52e5b44…`); suite green again. Full
record in `tests/README.md`.

## Core integrity

No pre-existing module was modified: `src/research/*.py` SHA-256
sums for all eight pre-existing modules match the pre-build
accounting exactly (store.py `ff43a9ac…`, the shipped hash
recorded in `scratch/store.py.sha256`; extensions.py
`9c82de73…`, the first unit's shipped hash). The addition is
store-level only (no HTTP routes), matching the sibling batch
units' pattern — the core `service.py` is byte-identical and
untouched.
