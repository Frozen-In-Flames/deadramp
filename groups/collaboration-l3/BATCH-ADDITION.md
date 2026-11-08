# Final GAPS batch — Remainder Addition — Collaboration L3-adjacent

This unit closes the 1 open entry of the GAPS.md section
"Remainder Addition — Collaboration L3-adjacent (+1 fork)"
(inventory idx 656) under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`. The section header, read verbatim from
GAPS.md and inventory.json, is:

## Remainder Addition — Collaboration L3-adjacent (+1 fork)

This is the **second** batch unit in this directory. The first
unit's note is `BATCH.md` (the Group 6 section, idx 72–80); this
unit covers the one gap `ADDENDUM.md` §5 registered when the
remainder fork Microsoft 365 Government Community Cloud
(`MSO365MTA`) joined the founding union.

What landed: one new module, `src/collab/extensions_addition.py`
(`CollabExtensionsAddition`, an independent second wrapper around
the core `CollabStore`; **all eight pre-existing modules — the
seven core modules and the first unit's `extensions.py` — stay
byte-identical**, SHA-256 verified against the pre-build baseline
in `scratch/prebatch-addition-src.sha256`; `store.py` still
`bd894169…`, the first unit's `extensions.py` still `f5de7aa2…`),
and `tests/test_gaps_batch_addition.py` (21 tests). This unit's
mutations are audited under the `exta_` action prefix, distinct
from the first unit's `ext_`. Full suite: **289 → 310 tests**, all
passing.

## Per-entry disposition

| Idx | Entry (GAPS.md text, verbatim) | Drafted triage | Disposition |
|---|---|---|---|
| 656 | Collaborative continuous monitoring service (the fork's closing sentence names an agency-vendor continuous-monitoring arrangement with no family in this taxonomy) | stub-engine | **reference** — labeled reference implementation, as drafted |

**No re-judgments.** DECISION.md qualification 1 was considered and
not needed: the drafted stub-engine disposition fits exactly. The
entry names a *service* — the agency–vendor continuous-monitoring
arrangement the fork's listing closes with ("Federal agencies
interested in collaborative continuous monitoring with Microsoft
should reach out to: …", ADDENDUM.md §2/§5). Monitoring runs
against live systems and agency networks; nothing in a records
substrate monitors anything, and a build claiming to watch the
substrate's own records would be a different (and smaller) thing
than the arrangement named. What ships is therefore the records
form of the arrangement, labeled as such:

- **Arrangement records** (`mon-`; the agency and vendor named by
  opaque references only, a cadence label from
  continuous/monthly/quarterly/annual, `reference_stub: True`,
  state `recorded_reference_only`, `monitored_here: False`).
  Registering one changes no core record — pinned behaviorally:
  the workspace and a core file record are byte-identical across a
  full register + report flow.
- **Monitoring-report records** (`monr-`; a period label, an
  outcome label from reported_current / reported_findings /
  reported_clean / reported_delayed, and a findings count held
  exactly as reported — a non-negative integer, booleans and
  floats rejected). There is no field that could hold report
  content; a smuggled `report_text=` (or `telemetry=` on the
  arrangement) raises `TypeError`.
- **Derived views** (`monitoring_view`, `monitoring_summary`):
  report counts, counts by reported outcome, the total of the
  recorded reports' findings counts (a sum of reported values,
  stated as such), and the current reported outcome — the latest
  recorded report's label, derived at read via
  `_latest_report_label` (this unit's fresh negative control) and
  stored nowhere; the stored arrangement record's exact key set is
  pinned free of every derived key.

ADDENDUM.md §5's own framing is preserved on the records' face:
this build's audit trail is the substrate such an arrangement
reports *from*, not the arrangement itself; no monitoring claim
is implied anywhere — `monitored_here: False` is stated on every
record.

Access discipline is carried from the core and the first unit:
every operation resolves its workspace through the core store, so
the membership boundary and the `read` permission bind reads and
writes alike; writes map to the core `post` action, denied write
attempts are audited `exta_*:denied`, and successful mutations land
on the same append-only, hash-chained log, recorded before the
record commits (AU-5 — an audit write failure changes nothing and
consumes no id, pinned by test). The **auditor role holds no
permission on this surface** — denied on every operation, reads
included — while its core audit duty still works (the chain
verifies `(True, None)` after a full flow, pinned). Nothing in
this surface computes a score: a recursive key scan over every
record, view, and the summary finds no
score/grade/rating/percent/rank key (pinned by test).

## Disclosed test strengthening

The first live drill run produced only 1 failure because the
view test's first and last report outcomes coincided
(`reported_findings` at both ends), so the earliest-reading mutant
satisfied it. The test's third report outcome was changed to
`reported_delayed` so the pin discriminates first from latest, the
drill was re-run clean (exactly 2 failures, below), and the suite
re-verified green. The module under test was never changed by
this; the correction is recorded here and in tests/README.md.

## Fresh negative control

The latest-report derivation,
`CollabExtensionsAddition._latest_report_label`. Live drill:
`extensions_addition.py` copied to
`scratch/extensions_addition.py.premutation` (SHA-256
`f11963bb…`), the seam's return patched
`reports[-1]["outcome_label"]` → `reports[0]["outcome_label"]`
(occurrence count asserted = 1): **310 ran, exactly 2 failures**,
both in `tests/test_gaps_batch_addition.py`
(`TestViews.test_view_derives_counts_total_and_current`,
`TestNegativeControlLatestReport.test_canonical_latest_label_wins`).
Restored from the premutation copy, SHA-256 verified identical,
suite re-ran green. Raw output:
`scratch/gaps_batch_addition_mutation_run.txt`; full record in
`tests/README.md`.

## Not covered by this unit

- The Group 6 founding section's entries (the first unit,
  `BATCH.md`) and the Collaboration L2 directory's units — both
  already shipped.
- Monitoring itself, in every sense: no system is watched,
  scanned, or collected from; no finding is produced or verified
  here. Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the service layer is untouched.
