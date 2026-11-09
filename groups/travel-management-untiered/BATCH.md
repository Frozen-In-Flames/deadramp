# Final GAPS batch — Untiered Set 28 — Travel Management

Unit: the open entries of the GAPS.md section
`## Untiered Set 28 — Travel Management (1 fork, tier null)`.

**Naming:** this is the FIRST batch unit in this directory — no
`extensions.py` / `test_gaps_batch.py` / `BATCH.md` existed
beforehand (the directory's only prior state is the founding
Phase 2 set build), so the unit landed with first-unit naming:
`src/travel/extensions.py`, `tests/test_gaps_batch.py`, and this
note. All 7 pre-existing `src/travel/` modules are byte-identical
to the pre-build baseline (SHA-256 verified against
`scratch/prebatch-src.sha256`; `store.py` still `a4098ea6…`).

**Entry count, verified against both sources, no discrepancy:**
GAPS.md and `gaps-batch/inventory.json` agree the section holds
2 entries: idx 966 open, and idx 967 "Platform layer" already
closed `re-scoped` at the batch foundation under
PLATFORM-LAYER.md — named here so the count reconciles; it is
not part of this unit and was not touched.

## Per-entry disposition

### idx 966 — built (as drafted, build-extension)

> Travel data aggregation & analytics engine (this fork's described function entire, registered in its own name, not from a claim)

Drafted triage: `build-extension` ("records/derivation-shaped;
buildable as an in-substrate extension of the owning group").
Closed as drafted — **no re-judgment** — with the entry's two
halves kept apart on every record's face, in the form the union
spec itself draws: the spec registers the gap as "collecting
travel data from source systems, aggregating it, and the
comprehensive reporting and analysis the aggregation supports,"
and distinguishes it from both the substrate's own summary
reporting (counts and sums over its own records) and the
report-generation gap (generation, not the pipeline feeding it).

What was built (`TravelExtensions` in
`src/travel/extensions.py`, audit prefix `ext_`):

- **Collection half — labeled reference.** Aggregation source
  records (`ags-`, the source system named by an opaque
  caller-supplied `source_ref` only — no field shape can hold a
  URL, host, or credential; kind from the surface's own
  vocabulary; optionally bound to a core integration definition
  by id, validated against the organization's registry) carrying
  `reference_stub: True`, `reference_transport: True`,
  `collected_here`/`connected_here: False`, state
  `recorded_reference_only`. A duplicate `source_ref` in one
  organization is refused whole by the
  `_check_source_ref_unique` seam (two records naming the same
  system would double-count its reports). Collection report
  records (`col-`) hold what a source reported, verbatim: an
  outcome label from the reported vocabulary and a record count
  held exactly as reported (`outcome_basis: source_reported`;
  booleans, floats, and negatives rejected with no id consumed).
  Nothing on this half connects, polls, or collects.
- **Aggregation half — built as derivation.** Aggregation
  profile records (`agp-`) hold a grouping as data
  (`definition_only: True`; creating one aggregates nothing)
  over the surface's four groupings: `expense_category`,
  `authorization_status`, `report_status`, `traveler`.
  `aggregation_view` derives the profile's groups at read —
  counts and integer-cent sums over the core's own recorded
  authorizations, expense reports, and expense items, read
  through the core store's public access-checked API — through
  the `_accumulate` seam, with the amount basis stated on the
  view's face per grouping (`figures_basis: core_records_only`;
  the view is never stored). A test pins that collection
  reports are never folded into these figures: a report of 999
  collected records leaves the view's totals exactly the core
  records' sums.
- **Summary.** `aggregation_summary` counts this surface's own
  records, sums the collection reports' counts stated as a
  `sum_of_reported_counts`, and derives the latest reported
  outcome label at read.

Doctrines held: money is integer cents only (every figure is a
sum of the core's recorded integer cents; no float value exists
on any record or view, pinned by recursive scan); **no per-diem
shape exists on the surface** — per-diem computation is a
recorded absence in this category and survives on this fork's
own words, so no method accepts a rate, day count, or allowance
and no record or view carries a per-diem key (pinned by
recursive scan and a signature scan over every public method);
nothing books, reserves, or pays (`booked_here: False` on
views); no score, rating, or risk key exists anywhere on the
surface (pinned); tier-null discipline pinned by the same
recursive scan (no tier / baseline / impact-level / equivalence
key). RBAC maps onto the core actions (profiles `enter`,
sources and collection reports `record`, reads `read`) with
denials audited as `ext_*:denied`; membership is enforced
through the core's access-checked organization read; audit
failure rolls back the create and its id (pinned); a full
extension flow leaves the core summary deep-equal (pinned).

## Verification

- Suite: **107 before → 135 after, all passing** (28 new tests
  in `tests/test_gaps_batch.py`); Python standard library only.
- **Fresh mutation-verified negative control:** the
  accumulation seam `TravelExtensions._accumulate` — in-suite
  three-leg control (canonical view carries the recorded sum /
  amount-blind mutant subclass sharing the canonical record
  tables / `assertRaises`) plus a live drill on the real
  `extensions.py` (the seam's amount line
  `entry[1] += amount_cents` patched to `entry[1] += 0`,
  occurrence count asserted = 1) → **135 ran, exactly 6
  failures**, all in the new module (the category, authorization
  status, report status, and traveler view tests, the
  collection-isolation test, and the control's canonical leg);
  all 107 pre-existing tests still passing. Restored from
  `scratch/extensions.py.premutation`, SHA-256 verified
  identical (`23abea02…`), suite re-ran green. Recorded in
  `tests/README.md`; raw output in
  `scratch/gaps_batch_mutation_run.txt`.

Nothing unresolved within the unit. Expected parent ship
arithmetic: 1 entry closed, token `built` (idx 966), exactly the
drafted disposition — no token overrides needed.
