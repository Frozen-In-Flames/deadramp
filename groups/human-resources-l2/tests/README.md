# Tests — Human Resources L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/human-resources-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 140 tests
```

Status at delivery: **77 tests, OK** against the implementation in
`../src/`. After the remainder additions (below): **89 tests, OK**,
implementation unchanged. After the final GAPS batch (below):
**140 tests, OK**, core implementation still unchanged — the batch
surface lives in the new `src/hr/extensions.py`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 11 RBAC — exact permission matrix for admin/hr_specialist/employee/auditor, `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | Core 12 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording each mutation action, failed ops record nothing |
| `test_persons.py` | Core 1 person records — exact record shape `{id, person_ref, kind, status, created_by, created_utc}`, `per-` ids, applicant vs employee initial status, duplicate person_ref rejected with no id consumed, status transitions, employee scope reads |
| `test_positions.py` | Core 2 position classification records — `pos-` ids, series/grade classification attributes (not pay data; no salary/compensation key), vacant/filled/abolished statuses, validation, employee/auditor write denied, org-level (unscoped) reads |
| `test_vacancies.py` | Core 3 vacancy announcements — `vac-` records bound to positions, draft/posted/closed statuses, ISO date validation (closes before opens rejected), unknown position, write roles |
| `test_applications.py` | Core 4 applications — `app-` records, stage vocabulary, duplicate live application rejected (allowed again after not_selected/withdrawn), unknown person/vacancy, employee scope, list filters |
| `test_evaluations.py` | Core 5 evaluation records — `evl-` records bound to applications, rater entries stored verbatim with **no aggregate/average/score field** (weighted cumulative scoring is Extended), duplicate rater rejected, rating must be a number (bool rejected), state transitions, employee scope through the application |
| `test_lifecycle.py` | Core 6 lifecycle cases & derived status — `lif-` onboarding/separation cases, `t-N` task checklists, derived status (not_started/in_progress/complete/cancelled) computed at read time and never stored, cancel as a recorded event, add_task moving a complete case back to in_progress, employee scope |
| `test_performance.py` | Core 7 performance reviews — `rev-` records with cycle + ISO period dates (end before start rejected), planned/in_progress/completed states, optional outcome label recorded, unknown person, employee scope |
| `test_benefits.py` | Core 8 benefits records — `ben-` benefit_enrollment/retirement_case records keyed by opaque plan_ref, pending/active/closed states, unknown person, employee scope |
| `test_cases.py` | Core 9 personnel cases — `cas-` personnel_action/award/labor_relations/general cases, opened/in_review/closed states, unknown person, employee scope |
| `test_reporting.py` | Core 10 reporting — counts over all record families, per-status/stage/state breakdowns, report lifecycle counts use derived status, employee denied `report_read`, empty-store shape |
| `test_privacy.py` | Privacy discipline (hard rule) — person record exact key set; walk one record of EVERY entity type asserting no key in the forbidden set {name, ssn, social_security_number, salary, compensation, pay, dob, date_of_birth, address, phone, email} |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (person → position → vacancy → application → evaluation + entry → lifecycle derived in_progress then complete → performance → benefits → case → report), employee write 403 + denied audited, employee scope over HTTP (403 on another person's application; org-level vacancy readable), audit admin+auditor only, report employee 403, 400/404 envelopes |
| `test_main_cli.py` | `python -m hr serve` subprocess with demo users alice/bob/carol/dana |
| `test_negative_control.py` | Negative control (below) |
| `test_additions.py` | Remainder additions (unit `addition:human-resources-l2`, see `../ADDENDUM.md`) — spec integrity: sheet count/unit order, membership vs `remainder.json`, literal per-fork claim table (GDC 9 / GRB 1 / Perceptyx 1), zero-claim families (16) pinned, near-miss pins (LERIS labor-relations phrasing, "role management", GRB "interface", Perceptyx "performance improvement"), wording-artifact pins (GDC benefits/awards/AI/audit), absence-update pins (leave retired; time & attendance retired by substance, literal probe still zero; payroll single external reference); substrate cases: GDC onboarding derivation + performance cycle + case kinds, GRB retirement/benefits records + employee scope, Perceptyx counts-only reporting + no-score scan |
| `test_gaps_batch.py` | Final GAPS batch (see `../BATCH.md`) — one class per open Extended entry: deterministic rule matching with evidence + employee-filtered matches; classification reference library + keyword recommendation/comparison derivations; job-analysis records; crediting plans (weights recorded as data, sum-to-100, panels-only, vacancy-bound); scoring views (exact-Fraction weighted cumulative + consensus mean/spread, pending criteria named, employee scope); the weighted-mean mutant negative control (below); certificates (referred-only assembly, derived entries, multi-person certificate denied to employees); outreach records (career sites, communities, events with derived registration count); mobility listings/interests + series-overlap match derivation; development programs/enrollments + derived summary; workforce analytics (counts + vacancy-rate bps) and scenario projections (integer derivation, nothing stored); retirement accrual estimate (integer derivation, `currency_amount` None, vesting, scope); learning catalog/assignments + derived summary; template assembly (placeholder validation against the source kind's recorded fields); the four stub surfaces (workflow definitions, posting receipts, assessment content/delivery, connectors/syncs, hosting) with `reference_stub` labels and core-unchanged pins; cross-cutting scans (no forbidden key, no aggregate key on any stored extension record), RBAC denials consuming no id, `ext_`-prefixed audit actions |
| `hr_helpers.py` | Shared fixtures: demo users (ADMIN/SPECIALIST/EMPLOYEE/AUDITOR), `USERS` registry, `fresh_store()`, and `make_store()` building an HrStore + AuditLog + one position ("Program Analyst", series "0343", grade "13", created by ADMIN) + one person (person_ref "carol", kind "employee", created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's negative
control: an `HrStore` subclass (`MutantHrStore`) whose
`_derive_case_status` always returns `"in_progress"` — the lifecycle
status derivation is skipped. The traced claim, named in the module's
docstrings, is that **lifecycle case status is derived
deterministically from the case's tasks and cancelled flag**: a case
whose every task is done/waived must read `complete`, and an
untouched case must read `not_started`. For each canonical case (all
tasks done, untouched case) the test asserts three things: the
canonical expectation (from the real implementation), that the mutant
would NOT produce that expectation (it says `in_progress` anyway),
and — via a literal `assertRaises(AssertionError)` — that treating
the mutant's outcome as the expected outcome fails. A third test
asserts the companion RBAC gate: an employee creating a position is
denied and the registry stays empty.

## Mutation verification

VERIFIED by the build worker (2026-10-25). The complete branch in
`HrStore._derive_case_status` (`src/hr/store.py`) — the line
`return "complete"` under
`if all(t["state"] in ("done", "waived") for t in tasks):` — was
patched to `return "in_progress"`, the exact live counterpart of the
mutant in `test_negative_control.py`, so a fully-completed lifecycle
case read `in_progress` instead of `complete`. The full suite was
run: **77 tests ran, 5 failed** —

- `test_lifecycle.TestLifecycle.test_add_task_appends_pending`
- `test_lifecycle.TestLifecycle.test_status_derivation_progression`
- `test_negative_control.TestNegativeControlMutantLifecycle.test_all_tasks_done_is_complete_canonical_but_mutant_in_progress`
- `test_reporting.TestReporting.test_report_lifecycle_uses_derived_status`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`ec34ab5e55f81b88a027aca6a29d024e18786f4791646dca7213b56f0a1061f0`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`) and the suite re-run: **77 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.

## Remainder additions — drill re-run (2026-10-31)

The remainder additions (unit `addition:human-resources-l2`,
`../ADDENDUM.md`) changed no core code, so the group's signature
drill was re-run in this tree: the complete branch of
`HrStore._derive_case_status` was patched exactly as in the
original drill (`return "complete"` → `return "in_progress"` under
the all-done/waived condition) and the full suite ran — **89
tests, exactly 7 failures**: the original drill's 5
(`test_lifecycle` add-task and derivation progression,
`test_negative_control` canonical case, `test_reporting` derived
status, `test_service` full flow) plus 2 from the new
`test_additions.py` (the GDC onboarding derivation case and the
Perceptyx counts-only reporting case), tripping exactly as
designed. `store.py` was restored from
`scratch/store.py.premutation-additions` and verified
SHA-256-identical to the shipped hash
(`ec34ab5e…`, matching `scratch/store.py.sha256`); the suite
re-ran green: **89 tests, OK**. Raw mutant output:
`scratch/additions_mutation_run.txt`.

## Final GAPS batch — fresh negative control (2026-11-07)

The batch lands new code (`src/hr/extensions.py`), so its negative
control is fresh, per `../../gaps-batch/DECISION.md`. The control
pins the batch's load-bearing computation: **the crediting plan's
recorded weights actually weight the weighted cumulative score
view**. `test_gaps_batch.TestWeightedMeanMutant` subclasses
`HrExtensions` with a mutant `_weighted_cumulative` that ignores the
weights (a plain mean of criterion means) and asserts the canonical
case both ways: criteria weighted 75/25 with verbatim-rating means
3 and 5 give a weighted cumulative of exactly 7/2 in the real
implementation and exactly 4 in the mutant, and treating the
mutant's 4 as the expectation raises `AssertionError`.

Mutation verification, performed on this build: the body of
`HrExtensions._weighted_cumulative` (`src/hr/extensions.py`) was
patched to the mutant's form —

```python
means = [mean for _, mean in weighted_means]
return sum(means, Fraction(0)) / len(means)
```

replacing the weighted sum — and the full suite ran: **140 tests,
exactly 2 failures** —

- `test_gaps_batch.TestScoringComputation.test_weighted_cumulative_exact_fraction`
- `test_gaps_batch.TestWeightedMeanMutant.test_weights_are_load_bearing_canonical`

`extensions.py` was then restored from the pre-mutation copy
(`scratch/extensions.py.premutation`; SHA-256
`f306310250e6cc8f77be0002f9152e58907f3437136beef2acd8ac2d2501eb84`,
verified identical after restore against
`scratch/extensions.py.sha256`) and the suite re-ran: **140 tests,
OK**. Raw mutant output: `scratch/gaps_mutation_run.txt`. The
group's original lifecycle-derivation drill above is untouched and
still passes as part of the 140.

## Final GAPS batch, second unit — remainder additions (2026-11-07)

The remainder-addition unit (see `../BATCH-ADDITION.md`) lands a
second extension module (`src/hr/extensions_addition.py`), so its
negative control is fresh, per `../../gaps-batch/DECISION.md`. The
new module `test_gaps_batch_addition.py` adds 36 tests (suite
**140 → 176, OK**): one class per remainder-addition entry — time
entries with derived effective minutes and leave balances derived
from recorded rates, accruals, and request states; org units and
assignments with the chart derived at read and freshness pinned;
survey instruments and verbatim bounded ratings with counts-only
summaries, listening signals as labels only, and multi-rater
feedback stored verbatim; benefits administration cases with
derived-never-stored status, employee scope through the bound
benefits record, and reported action/session records; portal
profiles stating their identity/serving boundaries, self-service
requests, and dashboard definitions pinned to an exact key set
with figures derived at read; uniform allowance requests in
integer cents with processing-step records and a derived summary —
plus cross-cutting scans (no forbidden key and no aggregate key
on any stored addition record; a signature scan asserting no
public method can accept a name, identifier, pay figure, or
free-text response content and that none takes `**kwargs`), RBAC
denials consuming no id, and `ext2_`-prefixed audit actions. The
control pins the unit's load-bearing derivation: **which recorded
request states count as used leave**. `TestLeaveBalanceMutant`
subclasses `HrExtensionsAddition` with a mutant
`_leave_used_minutes` that also counts merely-requested minutes as
used and asserts the canonical case both ways: 4,800 accrued
minutes with 600 approved and 300 still requested give a balance
of exactly 4,200 in the real implementation and exactly 3,900 in
the mutant, and treating the mutant's 3,900 as the expectation
raises `AssertionError`.

Mutation verification, performed on this build: the state tuple
on the `_leave_used_minutes` seam line in
`src/hr/extensions_addition.py` (line 483,
`if r["state"] in ("approved", "taken")`) was patched to
`("approved", "taken", "requested")` — the exact live counterpart
of the mutant — and the full suite ran: **176 tests, exactly 3
failures** —

- `test_gaps_batch_addition.TestLeaveBalanceMutant.test_used_minutes_seam_is_load_bearing`
- `test_gaps_batch_addition.TestTimeAttendanceLeave.test_employee_scope_on_leave_views`
- `test_gaps_batch_addition.TestTimeAttendanceLeave.test_leave_balance_derived_from_records`

`extensions_addition.py` was then restored from the pre-mutation
copy (`scratch/extensions_addition.py.premutation`; SHA-256
`461f5bcec5f53fe7dea4f2e1b80f8c946c3c63a4a252af79e69d4aa01784e521`,
verified identical after restore against
`scratch/extensions_addition.py.sha256`) and the suite re-ran:
**176 tests, OK**. Raw mutant output:
`scratch/gaps_addition_mutation_run.txt`. The group's original
lifecycle-derivation drill and the first batch unit's
weighted-mean drill above are untouched and still pass as part of
the 176.
