# Test suite — Human Resources untiered set (Set 16)

Standard-library `unittest` only. Run from this group's
directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**96 tests, all passing at delivery** (independently re-run by
the coordinator): 77 carried founding tests + 19 new spec tests.

## Layout

The carried suite is the founding Human Resources L2 group's
suite, copied whole — every test file except
`test_additions.py`, which pins the tiered additions census
unit and has no meaning in this set. The founding test module
docstrings identify the group as the tiered L2 group; they are
carried verbatim as part of the suite's provenance (the test
bodies are unchanged, and the suite tests the substrate, which
is itself byte-identical). `hr_helpers.py` is carried with one
edit: its module docstring names this untiered set.

| File | What it pins |
|---|---|
| `hr_helpers.py` | Shared constructors (carried; docstring edit only) |
| `test_persons.py` | Person records: opaque refs, exact key shape, status lifecycle, RBAC, audit |
| `test_positions.py` | Positions: creation, grade validation, fill/vacate/close, uniqueness |
| `test_vacancies.py` | Vacancy announcements: position binding, date validation, state machine |
| `test_applications.py` | Applications: stage machine, person/vacancy binding, RBAC scoping |
| `test_evaluations.py` | Evaluations: verbatim rater entries, no computed aggregate, auditor exclusion, no score field |
| `test_lifecycle.py` | Lifecycle cases: task checklists, derived status, stored record has no status key |
| `test_reviews.py` | Performance reviews: cycle states |
| `test_benefits.py` | Benefits & retirement records: state transitions |
| `test_cases.py` | Personnel cases: eight kinds, routing states |
| `test_reporting.py` | Reporting: counts over the records, lifecycle via derived status |
| `test_policy.py` | Policy guards: input validation, size caps, review states |
| `test_privacy.py` | Privacy: forbidden identifier keys rejected / absent on every entity shape |
| `test_service.py` | HTTP service: endpoints, JSON errors, full flow, stored-record status absence |
| `test_specs.py` | **This set's spec-integrity tests** (19 tests — below) |
| `test_negative_control.py` | The negative control (below) |
| `test_gaps_batch.py` | **Final GAPS batch unit tests** (36 tests — below) |

## Spec tests (`test_specs.py`, 19 tests)

- **Membership and tier discipline:** the specs are exactly the
  2 forks of census unit `untiered:Human Resources`, in unit
  order (Dayforce FR2633957417; Deltek - Replicon
  F1606087903); every sheet records `fedramp_impact_level`
  exactly "Unknown" and `cmmc_tier` null; vendor/product agree
  with `forks.json`; the as-filed categories are the recorded
  ones (Dayforce filed Analytics with source business
  categories [Analytics, Finance, Human Resources]; Replicon
  filed Uncategorized with []); `impact_basis` and
  `census_assignment` are recorded on every sheet; descriptions
  equal the census's uncovered descriptions exactly.
- **The literal claim table:** Dayforce's 5 claims in taxonomy
  order (`benefits_retirement`, `reporting_analytics`,
  `audit_compliance`, `integrations`, `access_control`),
  Replicon's 1 (`ai_automation`), set total 6; no zero-claim
  fork; the 6 claimed families and the 19 families at zero are
  pinned by name; every claim's evidence is a verbatim substring
  of its fork's own description under the house normalization.
- **Adjudication pins:** Replicon's claim stands at automation
  weight with no AI wording present; "workforce management"
  tags neither performance nor planning; the hiring chain is
  absent (10 families at zero, and the family's anchor
  vocabulary — "applicant", "vacancy", "onboarding",
  "performance", "personnel" — occurs in neither description);
  leave, policy, background-check, and salary/compensation
  absences stand in this set (the probed tokens literally
  absent); payroll is present in Dayforce's own capability
  list; time-and-attendance substance is present in Replicon
  ("timesheet", "time tracking"); Dayforce's Moderate/FIPS-199
  prose moves no tier (sheet fields pinned); the documented
  control phrases occur only in Dayforce's description.

## The negative control

`test_negative_control.py` (carried) drives a deliberately
incorrect derivation function inline: a mutant lifecycle
derivation that reports `in_progress` whenever no task is
pending — including the empty case — while the store's canonical
derivation reports `not_started`. The test asserts both
derivations are deterministic, that all-tasks-done is `complete`
canonically but `in_progress` under the mutant, and that the
stored record carries no status field at all. It passes only if
the derivation is genuinely computed at read time.

## Mutation-verification drill (recorded)

Founding group's signature drill, **re-run in this tree**. The
`complete` branch of `HrStore._derive_case_status` was mutated
so that an all-done/waived case derives `in_progress` instead
of `complete`:

- store.py SHA-256 before: `ec34ab5e55f81b88a027aca6a29d024e18786f4791646dca7213b56f0a1061f0`
  (recorded in `scratch/store.py.sha256`; identical to the
  founding group's post-restore hash in its own tests README —
  cross-checked before the drill ran)
- **exactly 5 tests fail** (raw output: `scratch/mutation_run.txt`):
  - `test_lifecycle.TestLifecycle.test_add_task_appends_pending`
  - `test_lifecycle.TestLifecycle.test_status_derivation_progression`
  - `test_negative_control.TestNegativeControlMutantLifecycle.test_all_tasks_done_is_complete_canonical_but_mutant_in_progress`
  - `test_reporting.TestReporting.test_report_lifecycle_uses_derived_status`
  - `test_service.TestFullFlow.test_full_flow`
- store.py restored from `scratch/store.py.premutation`; SHA-256
  after restore: `ec34ab5e55f81b88a027aca6a29d024e18786f4791646dca7213b56f0a1061f0`
  (**identical**). Full suite re-run after restore: **96 tests,
  OK**.

The 5 failing tests are exactly the founding group's original
drill result — every test that drives a case to completion and
reads its derived status, and nothing else. No spec test trips
under the mutation: spec integrity does not depend on the code
under test. (The tiered additions re-run of the same drill
failed 7; the 2 extra failures were in its additions module,
which this set does not carry.)

## Dependencies check

`scratch/verify_deps.py` scans `src/` for imports: the build
uses only the standard library (`argparse`, `dataclasses`,
`datetime`, `http`, `json`, `os`, `ssl`, `sys`, `threading`,
`urllib`). Result at delivery: **OK: stdlib only, zero
third-party imports**.

## Final GAPS batch unit (appended 2026-11-07)

`test_gaps_batch.py` (36 tests) pins the batch extension surface
(`src/hr/extensions.py`, `HrExtensions`) for this set's 7 open
entries (inventory idx 905–911): payroll run/statement records
with nets and totals derived at read and never stored; expense
reports with totals derived at read and approval as a recorded
label; time entries and schedule assignments with summaries
derived at read; communication metadata records with reported
delivery receipts (`reference_transport`); the document registry
(opaque refs + validated digests, current version derived at
read); and the two reference families (identity federation /
privileged access, security operations) carrying
`reference_stub: True` and state `recorded_reference_only`,
pinned to change no core record. Cross-cutting pins: the
tier-null recursive scan (no tier/cmmc/baseline/fedramp/impact
key on any stored record or derived view), the core forbidden-key
walk over the same surface, the no-PII signature scan (no
forbidden parameter name and no `**kwargs` on any public
method), TypeError on smuggled `email=` / `phone=` / `ssn=` /
`content=` keyword arguments, RBAC denials, employee scope,
failed operations consuming no id, and `ext_`-prefixed audit
entries on the core log. Full suite after the unit: **132 tests,
all passing** (96 before).

### Fresh negative control (mutation-verified)

The batch unit's signature seam is
`hr.extensions._derive_net_cents` — the single point where a pay
statement's net is derived (recorded gross minus recorded
deduction amounts, integer cents). `test_gaps_batch.py` carries
the in-suite control
(`TestNegativeControlPayrollNet`): the canonical seam returns
exactly 400000 for (500000, [75000, 25000]); with the module
global rebound to an adding mutant, the payroll view reports
600000 and the canonical expectation fails against it; after
restoring the binding the view returns 400000 again.

Live drill on the real `extensions.py`, recorded:

- extensions.py SHA-256 before:
  `66f20c4241abcbbe18ec4ed100460a0e296a8409a3bc1efd8f35700f8a455c3d`
  (recorded in `scratch/extensions.py.sha256`)
- the seam body `return gross_amount_cents - sum(deduction_amounts)`
  was patched to `return gross_amount_cents + sum(deduction_amounts)`
  (deductions added instead of subtracted)
- **exactly 3 tests fail** (raw output:
  `scratch/gaps_mutation_run.txt`):
  - `test_gaps_batch.TestPayroll.test_run_and_statement_net_derived_never_stored`
  - `test_gaps_batch.TestNegativeControlPayrollNet.test_canonical_net_subtracts_deductions`
  - `test_gaps_batch.TestNegativeControlPayrollNet.test_mutant_net_is_rejected_by_the_canonical_expectation`
- extensions.py restored from
  `scratch/extensions.py.premutation`; SHA-256 after restore:
  `66f20c4241abcbbe18ec4ed100460a0e296a8409a3bc1efd8f35700f8a455c3d`
  (**identical**). Full suite re-run after restore: **132 tests,
  OK**.

The 3 failing tests are exactly the ones that read a payroll net
through the seam; every other net-adjacent assertion reads gross
or deduction totals, which the sign flip does not touch, and no
carried founding test depends on the extension surface.
