# Final GAPS batch — Group 3, Analytics L3-adjacent

Unit: the 3 OPEN entries in GAPS.md under "Group 3 — Analytics
L3-adjacent (54 forks)" (idx 23–25 in
`../../gaps-batch/inventory.json`, all drafted `stub-engine`).
Dispositions per `../../gaps-batch/DECISION.md` (ratified
2026-11-07). **No re-judgments**: every entry fit its drafted
disposition on a close reading of the group's spec, in the forms
below. (The section's other five entries — idx 26–30, the
platform-layer baseline gaps — were already closed `re-scoped`
under PLATFORM-LAYER.md before this unit and are untouched.)

All extension code is in one new module, `src/analytics/extensions.py`
(`AnalyticsExtensions`, wrapping the core `DatasetStore`); every
existing core module is byte-identical to its pre-batch state
(SHA-256 verified for all 10; `query.py` still `f15c9b8f…`). Full
suite: 183 tests before, **206 tests after, OK** (23 new in
`tests/test_gaps_batch.py`), including the fresh mutation-verified
negative control recorded in `tests/README.md`.

Cross-cutting, per the group's doctrines and the High baseline:

- RBAC is enforced through the core `analytics.access` matrix — the
  extension maps each operation onto an existing core action (record
  creation/registration -> `ingest`; evaluations and views ->
  `query`) and checks it before any state change or id allocation;
  denied attempts are recorded on the core audit log as
  `ext_<action>:denied` and every successful mutation as
  `ext_<action>`. Validation runs before id allocation, so rejected
  input consumes no id. All dataset reads go through the core's
  public API.
- **The High apparatus binds the extension.** Extension audit
  entries are written on the core hash-chained log and carry
  `seq` / `prev_hash` / `hash` (AU-9). Extension mutations are
  **fail closed (AU-5)**, mirroring the core store's ingest
  rollback: if the audit write raises, the inserted record and the
  id allocation are rolled back and the error propagates (pinned
  by test against a broken JSONL path). The separated **auditor**
  role (AC-5) holds `audit_read` only, so it is denied every
  extension operation — mutations and views alike — with the
  denials audited; its core audit duty (`AuditLog.query`,
  `verify_chain()` -> `(True, None)` after a full extension flow)
  still works, pinned by test.
- Derived values (evaluation rollups, run counts, per-family
  report/receipt counts, reported-row totals) are computed at read
  and never stored; stored records carry no derived key, and tests
  pin that. Totals over reported row counts are sums of *reported*
  values and are named as such; nothing is measured or computed
  over external data. No cryptography of the build's own is
  performed anywhere on the surface (PLATFORM-LAYER.md decisions
  2–3); no signature-shaped entry appears in this section, so the
  Analytics L2 addition's digital-signature re-judgment precedent
  is noted but not needed here.

## Per-entry dispositions

| Entry (GAPS.md text) | Disposition | Built (module: `analytics/extensions.py`) |
|---|---|---|
| Alerts, monitoring & detection (27 of 54 forks claim it; kept Extended because each claimant binds alerting to its own domain telemetry — reasoning in the group spec) | reference | Labeled reference implementation in the Analytics L2 founding unit's adjudicated form: alert rule records over a core describe statistic (`alr-`, `reference_stub: True`, `state: recorded_reference_only`, `monitoring_here: False`) plus point-in-time evaluation receipts (`ale-`) — a deterministic comparison of the current core statistic against the recorded threshold, stored as a receipt (`method: recorded_evaluation_over_core_describe`). No watcher exists and nothing fires later; the receipt is not monitoring, and no monitor/watch/fire method exists on the surface (pinned by test). The spec's core-boundary reasoning is honored: each claimant's alerting binds to its own domain telemetry, which this build does not hold, so no generic monitoring is claimed. |
| Predictive ML remainder (family #1 at 34 of 54) | reference | Labeled reference implementation in the sibling units' adjudicated form: model reference records (`mdl-`, kind from the fixed vocabulary regression/classification/forecasting/clustering, `reference_stub: True`, `state: recorded_reference_only`, `trained_here: False`, `predicted_here: False`) and reported run records (`mdlr-`, outcome summary verbatim, reported figures held verbatim with `computed_here: False`, `executed: False`). There is deliberately no train, predict, fit, or infer method on the surface (pinned by test). The descriptive statistics the core already computes are not relabeled as ML. |
| Real-time / streaming (18), collaboration (17), proprietary connectors (17), governance (11), transformation (10), text/NLP (6), archiving (4), scheduling (3), geospatial (3), media analytics (2), self-service BI (2), KPI (0 claims in this group) | reference | Labeled reference implementation as one carried surface, in the Communication L3 bundled-entry form (idx 168 there): this tier's entry bundles twelve families into a single line, so there is **one reference record per family** (`efr-`, family validated against the exact 12-family set; the record carries the family's sibling count from the entry's own text as recorded data — including KPI's recorded zero, which stands — plus `reference_stub: True`, `implemented_here: False`) plus reported outcome records (`efp-`, outcome verbatim, reported figures verbatim, `performed_here: False`, `computed_here: False`) and, for the two transport-shaped families, the adjudicated reported-receipt forms bound to their family reference: stream batch receipts (`stmb-`, `reference_transport: True`, `ingested_here: False`, `streamed_here: False`; a test pins that recording batches leaves the core store's dataset set unchanged) and connector sync receipts (`cons-`, `reference_transport: True`, `connected_here: False`, `ingested_here: False`). Receipts bind only to their own family's reference (pinned). Per-family and bundle rollups are derived at read. |

**On the bundle's single token.** Several bundled families
(collaboration, governance, transformation, text/NLP, archiving,
scheduling, geospatial, media, self-service BI, KPI) have
records-shaped forms that sibling tiers built as separate entries
with separate tokens. Here they arrive as one line whose drafted
and honest token is `reference`: the line leads with the
transport/engine families (streaming 18, connectors 17), its
claim weight is engine-shaped, and — per the Communication L3
bundled-entry precedent — one reference record per family inside a
single carried surface does not re-token the bundle per family.
The records-shaped families are present by name with their counts
recorded, not silently dropped and not silently upgraded.

## Fresh negative control

The reported-rows total seam
(`AnalyticsExtensions._sum_reported_counts`): the canonical
expectation is that receipts reporting 4 and 3 rows derive a
`reported_rows_total` of 7 — the total is the SUM of the recorded
reports. The test module states the expectation once, asserts the
real implementation meets it (seam and family view), and asserts a
first-count-echo subclass mutant is rejected by it. Verified
against the real file by mutation (see `tests/README.md`):
patching the seam's return line to the echo form produced
exactly **5 failures** in 206, all in the new batch module; the
file was restored SHA-256-identical and the suite re-ran green.

## Verification

- Full suite on the final tree: **206 tests, OK** (183 pre-batch +
  23 new).
- Core byte-identity: SHA-256 of all 10 pre-existing
  `src/analytics/*.py` modules identical before and after
  (`query.py` still `f15c9b8f…`).
- Mutation drill: exactly 5 failures under the first-count-echo
  patch, restored and re-verified (raw output in
  `scratch/gaps_mutation_run.txt`; pre-mutation copy at
  `scratch/extensions.py.premutation_gaps`).
- Live smoke (parent-verifiable): alert rule + evaluation receipt
  over the canonical sales dataset (units mean 30.0, breached at
  threshold 25), model reference + reported run, streaming and
  connector family references with receipts (bundle reported-rows
  total 12), KPI family report with verbatim figures, auditor
  denied a rule creation with the denial audited, chain verifying
  `(True, None)`, and the core dataset set unchanged throughout.
- No core change was needed; nothing in the extension learns,
  predicts, monitors, streams, connects, executes a workflow, or
  performs cryptography.
