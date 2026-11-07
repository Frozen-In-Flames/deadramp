# Final GAPS batch — Untiered Set 7, Construction (6 forks, tier null)

Date: 2026-11-07. This section of `../../GAPS.md` listed 9 open
entries; all 9 are closed by this unit under the decisions in
`../../gaps-batch/DECISION.md` (ratified 2026-11-07) and
`../../PLATFORM-LAYER.md`.

What landed: one new module, `src/construct/extensions.py`
(`ConstructExtensions`, wrapping the core `ConstructStore`; all
seven core modules byte-identical, SHA-256 verified against the
accounting in this group's README — store.py still `49b5b203…`,
the shipped hash), and `tests/test_gaps_batch.py` (32 tests).
Full suite: **153 → 185 tests**, all passing.

**Tier discipline binds the extension surface exactly as it
binds the core.** The source publishes no FedRAMP impact level
for any member of this set, so tier stays null: no record shape
carries a tier, a baseline, or an equivalence, and a test scans
every extension record and derived view recursively for
tier-shaped keys, for floats, and for numeric lists. Nothing
here asserts a control baseline or draws a CMMC equivalence;
the forks' documented control claims remain the forks' claims
about themselves, recorded in `UNION-SPEC.md`.

The founding discipline binds every shape built here: this
build holds records about construction work. It commissions no
system, runs no estimating engine over proprietary data,
reviews no document, checks no specification, holds no
document content, senses no position, issues no permit,
assesses no asset's condition, executes no workflow, and runs
no model. Records carry metadata and opaque caller-supplied
references only, plus figures and outcomes stored exactly as
reported by the external systems and people who actually did
the work. That is pinned by exact key-set assertions per
record type, by `TypeError` on any unexpected keyword
argument, and by the recursive scan above. Every "engine"
below is its in-substrate form: records over the group's OWN
records (core records and extension records), plus
deterministic derivations at read.

## Per-entry disposition

| Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|
| Construction commissioning engine | built | Commissioning-plan records (`cxp-`) against a core project, checklist-item records (`cxi-`) in the platform's own kinds (installation checklist, functional performance test, issue & observation — the substance the union spec's named absence records), outcome records (`cxo-`) holding reported labels verbatim (`commissioned_here: False` — systems are verified by others; the records track), and turnover-package records (`cxt-`) holding an opaque package reference plus the core document ids it assembles (`assembled_here: False`). `commissioning_plan_view` derives item counts by kind, outcome counts by label, and the turnover count at read; the stored plan carries no counts. |
| Cost estimating engines & benchmark cost data | built | The founding group's adjudicated form: estimate records (`est-`) against a core project, holding the benchmark cost data as an opaque source reference only (`data_held_here: False` — no cost database is fabricated), plus line items (`estl-`) holding a recorded quantity and unit price (integer cents). Line totals and the estimate total are derived deterministically at read in `estimate_view`; stored lines carry no total key, and a test pins that recording estimates creates no core cost entries. |
| AI technical document review, UFGS checking & cited question-answering | built | Review-request records (`air-`) against a core document, in the set's claimed kinds (submittal review, UFGS check, design review, cited question-answering), plus result records (`aio-`) holding an opaque result reference and the reported outcome label verbatim. `reviewed_here` / `checked_here` / `answered_here` are False on the records; no extracted-text or findings field exists, and a cited answer is held as an `answer_ref` — a reference to an answer recorded elsewhere, never answer text (pinned by key scan and a `TypeError` test on an `answer_text` kwarg). No model runs here. |
| Document control platform depth | built | Document-control records (`dct-`) over core documents — one per document, holding a control label and an optional register reference (`content_held_here: False`; the core registry already holds metadata and version checksums only, never content) — plus approval records (`dap-`) holding reported decision labels verbatim (`approved_here: False`). `document_control_view` reads the core document (with its version history) at read time and derives the current approval label as the latest recorded decision; the stored control record carries no approval state. |
| GIS/spatial platform & asset location tracking | built | GIS layer records (`gis-`) as metadata for a core project, with geometry held as an opaque `geometry_ref` only (no geometry content or coordinates field exists; `rendered_here: False`), plus asset-location records (`loc-`) holding a reported position label verbatim (`tracked_here: False`). Each location record is standalone — no track/trail/history structure exists (pinned) — and an optional layer reference must belong to the named project. |
| Permitting, licensing & right-of-way management | built | Permit records (`prm-`) against a core project in the three recorded kinds (permit, license, right of way), holding authority and application references, plus append-only reported state records (`prs-`). The stored permit carries no state key; `permit_view` derives `current_state` at read by the seam `_current_permit_state` (latest recorded label wins — the batch's fresh negative control). `issued_here: False` — the authority issues; the records track. |
| Asset management platform (no taxonomy family exists for it in this category) | built | Asset records (`ast-`) in the set's own records form, keyed by a unique opaque `asset_ref` with kind/location labels and optional core project/org bindings; condition-assessment records (`asc-`) holding reported condition labels verbatim (`assessed_here: False` — nothing is assessed here); lifecycle capital-plan records (`cap-`) held as data (`executed_here: False`). `asset_summary` derives counts at read (assets by kind, assessments by reported condition, plan count) — counts only, no condition is computed and no score exists. |
| Workflow automation engines | reference | Labeled reference records: workflow definitions (`wfd-`) held as data — an ordered list of step labels stored verbatim, describing the lifecycles whose state machines are the in-core seed — plus reported outcome records (`wfo-`). Every record carries `reference_stub: True` and state `recorded_reference_only`; `executed_here: False`; the registry never executes (pinned: no run/execute API exists, and recording an outcome leaves the definition byte-identical). |
| Prevailing-wage determination depth (the standing gap; claimed in name only in this set) | built | The founding group's adjudicated form, exactly: rate tables (`rate-`) held as data (jurisdiction/trade labels, integer-cent-per-hour base and fringe rates); wage lines (`wage-`) holding recorded inputs only (rate-table reference, opaque worker reference, integer minutes — no amount stored); base, fringe, and gross computed deterministically at read by the seam `_compute_wage_amounts` in exact rational arithmetic (`Fraction`: rate x minutes / 60; a view renders an amount as an int when whole, else as an exact `"num/den"` string). Certified-payroll report records (`cpr-`) reference wage lines of one project/org; the report's totals exist only in `certified_payroll_view` — the stored report carries no totals and no core payroll record is created. E-filing ships as a labeled reference record (`efl-`, `reference_stub: True`, `filed_here: False`) inside the same entry: filing happens on the receiving agency's system. |

Closure tokens: 8 entries close as `built` and 1 as
`reference` (workflow automation engines, the section's one
stub-engine entry, at its drafted disposition).

## Re-judgments

None. Every build-extension entry was carried in the records
form the brief prescribes under the founding records
discipline, and the one stub-engine entry shipped as its
drafted labeled reference implementation. The calls nearest
the line are stated plainly rather than re-judged:

- **Prevailing wage** is built in two parts, exactly as the
  founding group's unit split it: rate tables, fringe
  calculation, and certified-payroll generation are genuine
  records derivations over recorded inputs (amounts computed
  at read, never stored, never rounded), while e-filing — an
  act performed on a receiving agency's system — ships inside
  the same entry as a labeled reference record with
  `filed_here: False`. The set's own caveat stands and is
  restated, not repaired: in this set the prevailing-wage
  family is claimed **in name only** (its three claims rest on
  wording artifacts — UFGS specification-compliance checking
  and a "high-compliance" adjective — per `UNION-SPEC.md`).
  The build is the records/arithmetic surface; it asserts the
  family's substance for no fork, and the entry's GAPS text
  itself carries the caveat.
- **Cost estimating** is built as computation records over
  recorded quantities and unit prices — not as an engine over
  a cost database: the benchmark cost DATA the entry names is
  held as a source reference only, and no cost figures are
  fabricated.
- **AI technical document review** closes `built` at its
  drafted build-extension disposition in the records form the
  brief prescribes (review requests plus opaque-reference
  results). This differs in token from the founding group's
  AI entry, which was drafted stub-engine and closed
  `reference`; the difference is the drafted disposition, not
  the substance — in both trees the build runs no model and
  holds no extracted text, and every record here carries
  `reviewed_here` / `checked_here` / `answered_here: False`.

## Negative control

Fresh, for the new code: the permit-state derivation seam
(`_current_permit_state` in `src/construct/extensions.py` — a
permit's current state is its latest recorded reported-state
label). In-suite control in `tests/test_gaps_batch.py`
(`TestPermitStateNegativeControl`: the canonical state sequence
yields `reported_issued` from both the seam and `permit_view`;
a local mutant reading the earliest label yields
`reported_submitted`, and treating the mutant's outcome as the
expectation fails via `assertRaises(AssertionError)`), plus a
live drill on the real file: the seam's return was patched to
`states[0]["state_label"]`, and the full suite ran **185 tests
with exactly 3 failures**, all in the batch's own new tests
(`TestPermitting.test_current_state_is_latest_recorded_label`,
`TestPermitStateNegativeControl.test_latest_canonical_but_mutant_not`,
`TestPermitStateNegativeControl.test_view_uses_the_seam`) — no
core test failed. The file was restored from
`scratch/extensions.py.premutation`, verified byte-identical by
SHA-256 (`scratch/extensions.py.sha256`), and the suite re-ran
green. Recorded in tests/README.md; drill output in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / honesty notes

- Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the core service layer is
  untouched.
- No record in this unit commissions a system, reviews a
  document, checks a specification, holds document content,
  senses a position, issues a permit, assesses an asset, or
  executes a workflow; the `*_here: False` labels are on the
  records themselves, not only in this document.
- Wage amounts are derived at read and rendered exactly;
  nothing in this unit rounds a wage figure. Where an amount
  is not a whole number of cents, the view carries its exact
  fraction as a string rather than a rounded integer.
- Tier null binds the whole unit: the extension asserts no
  baseline, draws no equivalence, and records no tier-shaped
  key anywhere (pinned by the recursive scan in
  `tests/test_gaps_batch.py`). The set's platform-layer
  paragraph in `UNION-SPEC.md` (multi-tenancy, encryption at
  rest, demo identities as hooks) is untouched by this unit;
  no entry in this section was triaged to the platform layer.
- The founding group's (Construction L2) own section entries
  belong to that group's batch unit; the forms here mirror
  them where this set's spec supports them, and nothing here
  re-closes them.
