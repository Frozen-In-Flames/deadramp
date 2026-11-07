# Final GAPS batch — Group 7, Analytics L1

Unit: the 8 OPEN entries in GAPS.md under "Group 7 — Analytics L1
(16 forks)" (inventory idx 64–71; 4 `build-extension`, 4
`stub-engine` in `../../gaps-batch/inventory.json`). Dispositions
per `../../gaps-batch/DECISION.md` (ratified 2026-11-07). The two
entries under the separate "Remainder Addition — Analytics L1"
section (idx 647–648) are not part of this unit and are untouched.

All extension code is in one new module, `src/analytics/extensions.py`
(`AnalyticsExtensions`, wrapping the core `DatasetStore`); every
existing core module is byte-identical to its pre-batch state
(SHA-256 verified for all 10; `query.py` still `f15c9b8f…`).
Full suite: 149 tests before, **172 tests after, OK** (23 new in
`tests/test_gaps_batch.py`), including the fresh mutation-verified
negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines and the Analytics L2 batch
unit's adjudicated forms where this tier's spec supports them:
RBAC is enforced through the core `analytics.access` matrix — each
operation maps onto an existing core action (record
creation/registration -> `ingest`, derivations and views ->
`query`) and is checked before any state change or id allocation;
denied attempts are recorded on the core audit log as
`ext_<action>:denied` and every successful mutation as
`ext_<action>`. Derived values (workspace counts, archive status,
transform run rollups, text-analysis rollups, all reference-surface
rollups) are computed at read and never stored; stored records carry
no derived key, and tests pin that. Validation runs before id
allocation, so rejected input consumes no id. All dataset reads go
through the core's public API. The baseline is fresh for L1: the
Low union, audit on the FedRAMP Low side only (FAR 52.204-21 carries
no audit practice); no Moderate/High apparatus is imported downward
from the L2 build.

**Two form-level notes (not re-judgments of disposition — every
entry closes with its drafted token):**

1. **Text / NLP** is built in the request-records form this unit's
   brief prescribes, not in the L2 unit's deterministic
   token-count form: at this tier the family has a single claimant
   and the honest in-substrate shape is request records plus
   results held as opaque refs or verbatim reported labels. No text
   is analyzed here (`analyzed_here: False` on both record kinds)
   and no text content is stored beyond what the core already
   holds; result records accept no text-content parameter
   (TypeError-pinned).
2. **Alerts / monitoring** follows the brief's stronger bound: the
   registry never evaluates or fires. Unlike the L2 unit, there is
   no point-in-time evaluation receipt and deliberately no evaluate
   method on the surface (absence pinned by test); alert
   occurrences arrive as reported records with verbatim statuses
   from a fixed vocabulary.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `analytics/extensions.py`) |
|---|---|---|
| Collaboration (3) | built | Workspace records, member records (opaque `member_ref`, recorded role), dataset share records, and annotation records over core datasets and opaque report refs (annotation text verbatim as the record's content); member/share counts and per-target annotation counts derived at read in `workspace_view` / `annotations_for`. Sharing is the records sense; no live co-editing is claimed. |
| Archiving (2) | built | Archive records over datasets and report refs. A dataset record carries a SHA-256 checksum computed at archive time over the core rows (metadata about the archived content) plus `disposition: record_only` / `retention_execution: embedding_organization` per PLATFORM-LAYER.md decision 4; a report target is an opaque ref and carries no checksum. Nothing is deleted or moved; a test pins that an archived dataset's rows are byte-for-byte still present. |
| Transformation (1) | built | Transformation definitions held as data: a named core query definition, validated by executing it once through the core at creation. `run_transform` derives the output through the core's existing deterministic query/aggregation machinery (`method: core_query_derivation`) and stores a run record holding counts and method only — never the derived rows. Runs performed outside are recorded as reported (`record_reported_transform_run`, counts verbatim, `executed_here: False`). No transform engine is invented; the derivation is the core's own machinery. |
| Text / NLP (1) | built | Text-analysis request records (dataset, column, kind from a fixed vocabulary) plus result records held as an opaque `result_ref` and/or verbatim reported labels; `analyzed_here: False` on both. See form note 1 above. |
| Real-time / streaming (8 of 16 — joint-largest family in this group, its biggest gap) | reference | Labeled reference implementation: stream-source definition records (`reference_stub: True`, `streamed_here: False`) and reported event-count records (`reference_transport: True`, `ingested_here: False`). Nothing ingests in real time; a test pins that recording reports leaves the core store's dataset set unchanged. |
| Proprietary-source connectors (5) — core covers open CSV/JSON only | reference | Labeled reference implementation: connector definition records (`reference_stub: True`, `connected_here: False`, `synced_here: False`) and reported sync records (rows verbatim, outcome label verbatim, `reference_transport: True`, `ingested_here: False`). The core's open CSV/JSON ingest coverage is unchanged and stated; a test re-exercises core CSV ingest after connector records exist. |
| Predictive ML, remainder of the statistics/ML family (5) | reference | Labeled reference implementation: model definition records (`reference_stub: True`, `trained_here`/`predicted_here`/`inference_here: False`), prediction-request records, and result records holding an opaque `result_ref` only (a `prediction=` value kwarg raises TypeError, pinned). There is deliberately no train or predict method on the surface (pinned). The descriptive statistics the core already computes are not relabeled as ML. |
| Alerts / monitoring (3) | reference | Labeled reference implementation: alert-rule definition records over a core describe statistic (`reference_stub: True`, `monitored_here`/`evaluated_here`/`fired_here: False`) plus reported alert records (status verbatim from a fixed vocabulary). The registry never evaluates or fires; no evaluate method exists on the surface (pinned). See form note 2 above. |

## Fresh negative control

The transform run-count seam (`_derive_rows_out`): the canonical
expectation is that a transform run over the canonical sales
dataset with a `region eq north` definition derives exactly the 3
north rows, and its run record reports rows_in 5 / rows_out 3. The
test module states the expectation, asserts the real implementation
meets it, and asserts a rows_out-echo subclass mutant
(rows_out := rows_in) is rejected by it. Verified against the real
file by mutation (see `tests/README.md`): patching the seam's
return line to `return rows_in` produced exactly 2 failures in 172;
the file was restored SHA-256-identical and the suite re-ran green.

## Verification

- Full suite on the final tree: **172 tests, OK** (149 pre-batch +
  23 new).
- Core byte-identity: SHA-256 of all 10 pre-existing
  `src/analytics/*.py` modules identical before and after.
- Mutation drill: exactly 2 failures under the rows_out-echo patch,
  restored and re-verified (raw output in
  `scratch/gaps_mutation_run.txt`; pre-mutation copy at
  `scratch/extensions.py.premutation_gaps`).
- No core change was needed; nothing in the extension learns,
  streams, connects, syncs, predicts, monitors, evaluates, fires,
  or deletes. No entry required a disposition re-judgment.
