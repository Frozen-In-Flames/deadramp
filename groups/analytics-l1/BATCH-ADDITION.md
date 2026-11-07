# Final GAPS batch — second unit: Remainder Addition — Analytics L1

Unit: the 2 OPEN entries of the GAPS.md section
**`## Remainder Addition — Analytics L1 (+1 fork)`** (the +1 fork
is HP Inc. / Workforce Experience Platform Collaboration,
`FR2017459185`, added to this group by the remainder census; its
spec sheet's `ADDENDUM.md` §5 registered these gaps). Built
2026-11-07 under `gaps-batch/DECISION.md` (the 2026-11-07
ratified triage) and `PLATFORM-LAYER.md`. Entry count verified
against both sources before building: GAPS.md's section lists
exactly 2 `- [] open` entries and `gaps-batch/inventory.json`
assigns exactly idx 647–648 to this section — **no discrepancy**
with the brief.

All extension code is one new module,
`src/analytics/extensions_addition.py`
(`AnalyticsExtensionsAddition`, a second wrapper around the
untouched core `DatasetStore`, audit actions prefixed `exta_`);
every existing module — including the first batch unit's
`extensions.py` — is byte-identical (SHA-256 verified against
the pre-build record in `scratch/prebatch-addition-src.sha256`;
`store.py` still `23bbca45…`, first-unit `extensions.py` still
`d6e1a389…`). Tests: `tests/test_gaps_batch_addition.py`
(18 tests; suite 172 → 190, all passing). Per-entry dispositions
below use the exact entry texts from GAPS.md /
`gaps-batch/inventory.json` (idx 647–648). The disposition
column is the closure token the parent records in GAPS.md.

Tier discipline: this is the L1 build — the Low/LI-SaaS union.
The addition rides the core's plain append-only audit log and
the admin/analyst/viewer matrix exactly as the first unit does;
no hash chain, lockout, or auditor role is imported downward
from the High sibling.

| idx | Entry (verbatim) | Drafted | Closed as | What landed |
|---|---|---|---|---|
| 647 | Collaboration & unified-communications telemetry engine: multi-vendor UC telemetry collection, experience visibility / insights (the fork's whole product; named separately from the generic alerts gap, which covers engines over data already in the platform) | stub-engine | **reference** | Labeled reference implementation: telemetry source definition records (`uct-`: name, `vendor_label` recorded as data — multi-vendor is the entry's substance, `source_kind` from a recorded vocabulary; `reference_stub: True`, `state: recorded_reference_only`, `collected_here` / `connected_here`: False) and reported telemetry records (`uctr-`: session counts and minutes **as reported**, aggregates only — no session content, no user data, the metadata-only shape `test_additions.py` exercises this fork against the core in; `reference_stub` + `reference_transport: True`, `collected_here` / `ingested_here`: False; outcome label verbatim). `telemetry_source_view` derives the report count and the reported session/minute totals at read as sums of the recorded reports. A test pins that recording reports leaves the core store's dataset set unchanged, and that no collect/connect/poll/subscribe/stream method exists on the surface. The collection plane itself — continuous telemetry collection from live UC environments — is an engine over external systems and is not operated here; the entry's own distinction from the founding section's alerts gap (engines over data already in the platform) is preserved: this surface is the upstream plane's records form, not an alerting form. |
| 648 | End-user experience & productivity analytics engine (by substance; no family claims it, no score defined or computed) | build-extension | **built** | Experience profile records (`exp-`: a named core dataset + one of its columns, held as a definition only — the stored record carries **no figure of any kind**, exact key set pinned by test; `method: core_describe_derivation`, `basis: recorded_dataset_values`, `measured_here`: False) and experience observation records (`expo-`: dimension from a recorded vocabulary — call quality, meeting reliability, join experience, audio/video quality, productivity, IT efficiency, the dimensions the fork's prose names; label and covering count recorded **verbatim as reported**; `measured_here` / `computed_here`: False). `experience_view` derives at read: the core's own `describe` statistics over the profile's recorded dataset column (surfaced verbatim from the core machinery and labeled `statistics_basis: recorded_dataset_values`), plus the observation rollup (count, sum of reported counts, counts by dimension and by label). **No score exists on this surface**: the entry's own parenthetical is honored literally — a recursive scan of every record and view pins the absence of any score-shaped key, and no method accepts a score parameter (`score=` / `score_threshold=` raise TypeError, pinned). What is built is the records-plus-derivation surface over data the substrate already holds; no live user is measured and no productivity figure is computed from anything. |

## Re-judgments (DECISION.md qualification 1)

None. Both entries close with their drafted dispositions, each
bounded as its row states:

- idx 647's drafted `stub-engine` triage is the honest reading:
  the entry names a collection engine over external UC
  environments (the fork's whole product is the upstream
  telemetry plane), and engines over external systems ship as
  labeled reference implementations under the ratified split.
  Nothing in this substrate collects, and the records form
  (source definitions plus reported aggregate counts) claims
  nothing more.
- idx 648's drafted `build-extension` triage stands because the
  substance genuinely has an in-substrate records form: the
  substrate already holds UC-telemetry-shaped datasets (the
  addition's own substrate tests ingest them), and the core's
  descriptive statistics over recorded values plus recorded
  experience observations are derivations over the substrate's
  own records — the same built grammar the first unit used for
  transformation (derivations through the core's machinery).
  The bound the entry itself states — no score defined or
  computed — is preserved as a structural property of the
  surface, not a disclaimer: there is no score-shaped key and
  no parameter that could carry one.

## Negative control

Fresh, for this surface: the reported-counts sum seam
(`AnalyticsExtensionsAddition._sum_reported_counts`). The
canonical rule: every reported total on this surface — a
telemetry source's reported session/minute totals, an
experience profile's reported-observations total — is the sum
of *every* recorded report; a total that merely echoes the
first reported count understates it and is the mutant. The
in-suite three-leg control in `test_gaps_batch_addition.py`
(`TestReportedCountsNegativeControl`): canonical views over
two-report histories (4 + 3 sessions, 300 + 150 minutes) read 7
and 450; the first-count-echo subclass mutant reads 4; a
literal `assertRaises(AssertionError)` pins that the mutant's
totals are rejected by the canonical expectation. Verified
against the real file by live drill: the seam's return line
(`return sum(counts)`, exactly one occurrence, asserted before
patching) was patched to `return counts[0] if counts else 0`
and the full suite ran — **190 tests, exactly 3 failures**, all
in the new module and all tripping on a reported total exactly
as designed:

- `TestTelemetryReference.test_view_totals_are_sums_of_reports`
- `TestExperienceBuilt.test_view_observation_rollup_derived_at_read`
- `TestReportedCountsNegativeControl.test_canonical_totals_sum_all_reports`

The file was restored from the pre-mutation copy
(`scratch/extensions_addition.py.premutation`) and verified
SHA-256-identical to the pre-drill hash (`be2d1699…`); the
suite re-ran green (190 tests, OK). Raw drill output is kept at
`scratch/gaps_addition_mutation_run.txt`. Recorded in
`tests/README.md`.

## Verification

- Full suite on the final tree: **190 tests, OK** (172
  pre-unit + 18 new).
- Core byte-identity: SHA-256 of all 11 pre-existing
  `src/analytics/*.py` modules identical before and after
  (`scratch/prebatch-addition-src.sha256`), including the first
  unit's `extensions.py`.
- Live smoke (in-process): telemetry source registered, two
  reports recorded (12 + 8 sessions, 540 + 360 minutes) → view
  totals 20 / 900 with the core dataset set unchanged;
  experience profile over the canonical sales dataset →
  statistics count 5 / mean 30.0 (the core's describe, exactly),
  two observations → rollup total 12; all four `exta_` audit
  actions present on the core log.
- Standard library only (imports: `copy`, `threading`,
  `datetime`, plus intra-package modules) — no third-party
  dependency, no cryptography of any kind.
- Nothing in this unit collects, connects, ingests, streams,
  measures a live user, or computes a score.
