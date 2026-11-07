# Final GAPS batch — Group 19, Construction L2

Date: 2026-11-07. This section of `../../GAPS.md` listed 9 open
entries (inventory idx 204–212); all 9 are closed by this unit
under the decisions in `../../gaps-batch/DECISION.md` (ratified
2026-11-07) and `../../PLATFORM-LAYER.md`.

What landed: one new module, `src/construct/extensions.py`
(`ConstructExtensions`, wrapping the core `ConstructStore`; all
seven core modules byte-identical, SHA-256 verified against the
pre-build sums — store.py still `49b5b203…`, the shipped hash),
and `tests/test_gaps_batch.py` (31 tests). Full suite: **146 →
177 tests**, all passing.

The founding discipline binds every shape built here: this build
holds records about construction work. It runs no estimating
engine over proprietary data, senses no position, monitors no
vehicle, executes no workflow or signature, and runs no model.
Records carry metadata and opaque caller-supplied references
only, plus figures and outcomes stored exactly as reported by
the external systems and people who actually did the work. That
is pinned by exact key-set assertions per record type, by
`TypeError` on any unexpected keyword argument, and by a
no-float scan over the extension surface. Every "engine" below
is its in-substrate form: records over the group's OWN records
(core records and extension records), plus deterministic
derivations at read.

## Per-entry disposition

| # | Entry (GAPS.md text) | Disposition | Built as |
|---|---|---|---|
| 204 | Cost estimating engines & the proprietary cost data behind them (estimate records are Core) | built | Estimate records (`est-`) against a core project, holding the proprietary cost data as an opaque source reference only (`data_held_here: False` — no cost database is fabricated), plus line items (`estl-`) holding a recorded quantity and unit price (integer cents). Line totals and the estimate total are derived deterministically at read in `estimate_view` (quantity x unit price, exact); stored lines carry no total key, and a test pins that recording estimates creates no core cost entries. |
| 205 | GPS / location tracking platform & mobile field data collection | built | Field-report records (`fld-`): a reported position label and an observation label stored verbatim as reported (`tracked_here: False`, `collected_here: False`). Positions are caller-reported data, never sensed; each report is standalone and no continuous tracking state exists (pinned: no track/trail/history structure on any report). An optional dispatch reference must name a core dispatch of the same project. |
| 206 | Fleet & vehicle telematics (vehicle monitoring, driver-behavior score cards) | reference | Labeled reference records: vehicle records (`veh-`) holding an opaque vehicle reference (`monitored_here: False`) and telematics reports (`tel-`) holding the platform's report label verbatim. A driver-behavior score is a REPORTED label only (`reported_driver_score_label`, a string stored verbatim) — a test pins that it is the only score-shaped key on the record and that no score is computed anywhere. |
| 207 | Contract-lifecycle workflow engines, template & clause libraries, negotiation playbooks with redlining | reference | Labeled reference records: template records (`tpl-`) and clause records (`cls-`) as metadata only (no content/text field exists), playbook records (`pbk-`) as metadata, and negotiation outcome records (`neg-`) against a core contract holding the outcome label verbatim (`redlined_here: False`). A test pins that recording an outcome leaves the core contract view byte-identical. |
| 208 | E-signature execution | reference | Labeled reference records in the house form: signature requests (`sig-`) naming exactly one of a core contract or a core document plus an opaque signer reference, and outcome records (`sigo-`) holding the signing service's reported label verbatim. `signed_here: False` on both shapes; no signature-value field exists (pinned by key scan). |
| 209 | AI/ML models (AI data extraction & negotiation assistance) (1) | reference | Labeled reference records: extraction results (`aix-`) against a core document and negotiation-assistance results (`ain-`) against a core contract, each holding a model label and an opaque result reference only. `inference_here: False`; no extracted-text or advice field exists (pinned by key scan). |
| 210 | Workflow / process automation engines (2; lifecycle state machines are the in-core seed) | reference | Labeled reference records: workflow definitions (`wfd-`) held as data — an ordered list of step labels stored verbatim, describing the lifecycles whose state machines are the in-core seed — plus reported outcome records (`wfo-`). `executed_here: False`; the registry never executes (pinned: no run/execute API exists, and recording an outcome leaves the definition byte-identical). |
| 211 | Prevailing-wage determination depth (rate tables, fringe calculation, certified-payroll generation / e-filing) | built | Built genuinely where arithmetic suffices: rate tables (`rate-`) held as data (jurisdiction/trade labels, integer-cent-per-hour base and fringe rates); wage lines (`wage-`) holding recorded inputs only (rate-table reference, opaque worker reference, integer minutes — no amount stored); base, fringe, and gross computed deterministically at read by the seam `_compute_wage_amounts` in exact rational arithmetic (`Fraction`: rate x minutes / 60; a view renders an amount as an int when whole, else as an exact `"num/den"` string). Certified-payroll report records (`cpr-`) reference wage lines of one project/org; what is derived is exactly the report's totals, which exist only in `certified_payroll_view` (exact sums of the seam over the lines, plus line and distinct-worker counts) — the stored report carries no totals and no core payroll record is created. E-filing ships as a labeled reference record (`efl-`, `filed_here: False`): filing happens on the receiving agency's system. |
| 212 | Dispatch routing & optimization | built | Route records (`rte-`) against a core dispatch, held as data: an ordered list of stop labels stored verbatim in the caller's recorded order, plus outcome records (`rto-`) holding reported labels verbatim. `optimized_here: False` on both shapes — no optimizer runs; a route is a recorded plan, not a computed one. A test pins that recording a plan leaves the core dispatch record byte-identical, and `route_view` puts the plan, its outcomes, and the core dispatch side by side. |

Closure tokens: 4 entries close as `built` (204, 205, 211,
212) and 5 as `reference` (206, 207, 208, 209, 210).

## Re-judgments

None. Every build-extension entry was carried in the records
form the brief prescribes under the founding records
discipline, and all five stub-engine entries shipped as their
drafted labeled reference implementations. The calls nearest
the line are stated plainly rather than re-judged:

- **Prevailing wage (211)** is built in two parts, exactly as
  the entry's own text splits: rate tables, fringe calculation,
  and certified-payroll generation are genuine records
  derivations over recorded inputs (amounts computed at read,
  never stored; a non-whole amount is rendered as its exact
  fraction rather than rounded), while e-filing — an act
  performed on a receiving agency's system — ships inside the
  same entry as a labeled reference record with
  `filed_here: False`. The entry closes `built` on its drafted
  disposition; the e-filing record's reference form is stated
  on the record itself.
- **Cost estimating (204)** is built as computation records
  over recorded quantities and unit prices — not as an engine
  over a cost database: the proprietary cost DATA the entry
  names is held as a source reference only, and no cost
  figures are fabricated. The parenthetical in the entry's own
  text ("estimate records are Core") bounds it the same way.

## Negative control

Fresh, for the new code: the prevailing-wage seam
(`_compute_wage_amounts` in `src/construct/extensions.py` — a
wage line's fringe is computed from the recorded fringe rate
and included in the gross). In-suite control in
`tests/test_gaps_batch.py` (`TestWageSeamNegativeControl`: the
canonical case yields fringe 4000 and gross 28000 from both the
seam and the view; a local mutant dropping the fringe does not
produce the canonical gross, and treating the mutant's gross
as the expectation fails), plus a live drill on the real file:
the seam's fringe term was patched to `Fraction(0)`, and the
full suite ran **177 tests with exactly 4 failures**, all in
the batch's own wage tests
(`TestPrevailingWage.test_wage_amounts_derived_exact_never_stored`,
`TestPrevailingWage.test_certified_payroll_report_totals_derived`,
`TestWageSeamNegativeControl.test_fringe_canonical_but_mutant_not`,
`TestWageSeamNegativeControl.test_view_uses_the_seam`) — no core
test failed. The file was restored from
`scratch/extensions.py.premutation`, verified byte-identical by
SHA-256 (`scratch/extensions.py.sha256`), and the suite re-ran
green. Recorded in tests/README.md; drill output in
`scratch/gaps_batch_mutation_run.txt`.

## Not covered / honesty notes

- Store-level surface only (no HTTP routes), matching the
  sibling batch units' pattern; the core service layer is
  untouched.
- No record in this unit senses a position, monitors a
  vehicle, signs anything, runs a model, optimizes a route, or
  executes a workflow; the `*_here: False` labels are on the
  records themselves, not only in this document.
- Wage amounts are derived at read and rendered exactly;
  nothing in this unit rounds a wage figure. Where an amount
  is not a whole number of cents, the view carries its exact
  fraction as a string rather than a rounded integer.
- This group's own platform-layer notes in UNION-SPEC
  (multi-tenancy, encryption at rest, demo identities as
  hooks) are untouched by this unit; no entry in this section
  was triaged to the platform layer.
