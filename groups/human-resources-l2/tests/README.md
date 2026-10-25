# Tests — Human Resources L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/human-resources-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 77 tests
```

Status at delivery: **77 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
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
