# Final GAPS batch — Group 1, Analytics L2

Unit: the 14 entries in GAPS.md under "Group 1 — Analytics L2
(128 forks)" (10 `build-extension`, 4 `stub-engine` in
`../../gaps-batch/inventory.json`). Dispositions per
`../../gaps-batch/DECISION.md` (ratified 2026-11-07). **No
re-judgments**: every entry fit its drafted disposition on a close
reading of the group's spec, in the forms below.

All extension code is in one new module, `src/analytics/extensions.py`
(`AnalyticsExtensions`, wrapping the core `DatasetStore`); every
existing core module is byte-identical to its pre-batch state
(SHA-256 verified for all 10). Full suite: 147 tests before,
**176 tests after, OK** (29 new in `tests/test_gaps_batch.py`),
including the fresh mutation-verified negative control recorded in
`tests/README.md`.

Cross-cutting, per the group's doctrines: RBAC is enforced through
the core `analytics.access` matrix — the extension maps each
operation onto an existing core action (the core action set is
fixed: record creation/registration -> `ingest`, derivations and
views -> `query`, governance access-review decisions -> `admin`)
and checks it before any state change or id allocation; denied
attempts are recorded on the core audit log as `ext_<action>:denied`
and every successful mutation as `ext_<action>`. Derived values
(workspace counts, transform run rollups, governance rollups, KPI
values and deltas, schedule rollups, media totals, geospatial
distances/bearings) are computed at read and never stored; stored
records carry no derived key, and tests pin that. Validation runs
before id allocation, so rejected input consumes no id. All dataset
reads (existence, rows, queries, descriptive statistics) go through
the core's public API — the extension re-implements none of it.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `analytics/extensions.py`) |
|---|---|---|
| Collaboration (shared workspaces around analytics) | built | Workspace records, member records (opaque `member_ref`, recorded role), share records for core datasets and saved views; member/share counts derived at read in `workspace_view`. |
| Data transformation / ETL | built | Transformation definitions as ordered stated rules from a fixed step vocabulary (rename, select_columns, filter, sort, limit), validated against the dataset's columns at definition time. `run_transform` derives the output rows deterministically over the core dataset (`method: deterministic_rules`) and stores a run record holding counts and method only — never the derived rows. Runs beyond the stated rules are recorded as reported (`record_reported_transform_run`, counts verbatim, `reported: True`). |
| Governance beyond the dataset registry | built | Policy records over core datasets (classification, access_review, quality_rule, retention_note) and access-review decision records (decision verbatim, mapped to the core `admin` action); per-dataset rollup with current decision derived at read. |
| Geospatial analytics | built | Place records holding a named coordinate pair only; distance (haversine, `method: haversine_great_circle`), initial bearing, and nearest-place are exact deterministic derivations at read, never stored on the record (record key set pinned by test). |
| Text / NLP analytics | built | Deterministic tokenization/count derivations over text the core already holds: term counts and top-terms (`method: deterministic_token_count`), plus exact per-term counts. Counts only — no learned model, no classification, no sentiment; nothing is stored. |
| Archiving | built | Archive records over datasets, saved views, and report refs, each labeled `disposition: record_only` / `retention_execution: embedding_organization` per PLATFORM-LAYER.md decision 4. Nothing is deleted or moved; a test pins that an archived dataset's rows are byte-for-byte still present. |
| Self-service BI | built | Saved-view records storing a named core query definition (validated by executing it once through the core at creation); running a view derives its result live from the core and stores nothing on the record (pinned). Dashboard records with panel records bound to saved views; panel view names resolved at read. |
| KPI management | built | KPI definitions storing a measure (core `describe` statistic, or a core aggregate with optional `where`) and an optional target as data — no value on the record (pinned). `kpi_value` derives the current value (and the delta against the target) at read from the core statistics/query surfaces. |
| Scheduling | built | Schedule definition records (target kind + cadence as recorded data) plus run receipts recorded as reported, each carrying `executed_here: False` — nothing in the build runs on a timer. Run rollups and last outcome derived at read. |
| Media analytics | built | Media metadata records only (opaque `media_ref`, kind, optional duration/format, `analysis: metadata_only`); the build holds no media content and analyzes none. Summary counts and total duration derived at read. |
| Predictive ML (the remainder of the statistical/ML claim family; core covers descriptive statistics only) | reference | Labeled reference implementation: model reference records (`reference_stub: True`, `state: recorded_reference_only`, `trained_here: False`) and reported run records (`executed: False`). There is deliberately no train or predict method on the surface (pinned by test). |
| Alerts, monitoring & detection | reference | Labeled reference implementation: alert rule records over a core describe statistic (`reference_stub: True`, `monitoring_here: False`) plus point-in-time evaluation receipts — a deterministic comparison of the current core statistic against the recorded threshold, stored as a receipt (`method: recorded_evaluation_over_core_describe`). No watcher exists and nothing fires later; the receipt is not monitoring. |
| Real-time / streaming analytics | reference | Labeled reference implementation: stream reference records (`reference_stub: True`, `streaming_here: False`) and reported batch receipts (`reference_transport: True`, `ingested_here: False`). A test pins that recording batches leaves the core store's dataset set unchanged. |
| Proprietary-source connectors (core covers open-format file ingest only) | reference | Labeled reference implementation: connector reference records (`reference_stub: True`, `connected_here: False`) and reported sync receipts (`reference_transport: True`, `ingested_here: False`). Core ingest (open CSV/JSON) is unchanged and nothing connects. |

## Fresh negative control

The transform filter seam (`_apply_transform_steps` /
`_apply_step`): the canonical expectation is that a
`region eq north` filter run over the canonical sales dataset
returns exactly the 3 north rows. The test module states the
expectation, asserts the real implementation meets it, and asserts
a filter-blind subclass mutant is rejected by it. Verified against
the real file by mutation (see `tests/README.md`): patching the
filter branch to return `list(rows)` unfiltered produced exactly
2 failures in 176; the file was restored SHA-256-identical and the
suite re-ran green.

## Verification

- Full suite on the final tree: **176 tests, OK** (147 pre-batch +
  29 new).
- Core byte-identity: SHA-256 of all 10 pre-existing
  `src/analytics/*.py` modules identical before and after
  (`query.py` still `f15c9b8f…`).
- Mutation drill: exactly 2 failures under the filter-blind patch,
  restored and re-verified (raw output in
  `scratch/gaps_mutation_run.txt`).
- No core change was needed; nothing in the extension executes
  against an external system, learns, streams, monitors, or
  deletes.
