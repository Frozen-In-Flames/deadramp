# Tests — Education & Training L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/education-training-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 65 tests
```

Status at delivery: **65 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/instructor/learner/auditor, `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording each mutation action, failed ops record nothing |
| `test_courses.py` | Core 1 course/catalog registry — creation shape/provenance, `crs-` ids, course vs program kinds, get/list sorted, validation, catalog_write admin-only, unknown id |
| `test_enrollments.py` | Core 2 enrollments & registrations — enrollment + registration kinds, duplicate active enrollment rejected with no id consumed, unknown course, learner write denied, learner scope reads, list filters |
| `test_progress.py` | Core 3 progress & readiness records — `prg-` shape, readiness/percent, completion as terminal state record, validation (bad status/readiness/percent, unknown course), learner scope |
| `test_assessments.py` | Core 4 assessment records — `asm-` administration records, item responses stored verbatim with **no score/grade field** (scoring is Extended, 0/8), duplicate item rejected, state transitions, session binding, learner scope |
| `test_credentials.py` | Core 5 credential records — `cred-` records with ISO issued/expiry dates, status update as record change, date validation, credential_write admin-only, learner scope. Records only; no issuance |
| `test_compliance.py` | Core 6 compliance assignments & derived status — stored record carries **no status field**, overdue/current/completed derivation against explicit `as_of`, on-due-date is current, completion overrides overdue, in_progress does not complete, derivation deterministic in `as_of`, admin-only writes, learner scope |
| `test_scheduling.py` | Core 7 scheduling records — `sch-` training/assessment sessions bound to courses and learner ids, assessment record referencing a session, ends-before-starts/bad kind/malformed datetime validation, role gates |
| `test_reporting.py` | Core 8 reporting — counts over all record families, per-status breakdowns, enrollments by course, report compliance counts use derived status at `as_of`, learner denied `report_read`, empty-store shape |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (course → enroll → session → assessment + response → credential → compliance derived overdue → progress completed → derived completed → report), learner write 403 + denied audited, learner scope over HTTP (403 on another learner's enrollment), audit admin+auditor only, report learner 403, 400/404 envelopes |
| `test_main_cli.py` | `python -m learn serve` subprocess with demo users alice/bob/carol/dana |
| `test_negative_control.py` | Negative control (below) |
| `learn_helpers.py` | Shared fixtures: demo users (ADMIN/INSTRUCTOR/LEARNER/AUDITOR), `USERS` registry, `fresh_store()`, and `make_store()` building a LearnStore + AuditLog + one course (created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's negative
control: a `LearnStore` subclass (`MutantLearnStore`) whose
`_derive_status` always returns `"current"` — the compliance status
derivation is skipped. The traced claim, named in the module's
docstrings, is that **compliance status is derived deterministically
from assignment, due date, and progress records**: a past-due
incomplete assignment must read `overdue`, and an assignment with a
completed progress record must read `completed`. For each canonical
case (past-due incomplete, completed) the test asserts three things:
the canonical expectation (from the real implementation), that the
mutant would NOT produce that expectation (it says `current`
anyway), and — via a literal `assertRaises(AssertionError)` — that
treating the mutant's outcome as the expected outcome fails. A third
test asserts the companion RBAC gate: a learner creating a course is
denied and the registry stays empty.

## Mutation verification

VERIFIED by the build worker (2026-10-25). The overdue branch in
`LearnStore._derive_status` (`src/learn/store.py`) — the line
`return "overdue"` under `if as_of_date > due:` — was patched to
`return "current"`, the exact live counterpart of the mutant in
`test_negative_control.py`, so a past-due incomplete assignment read
`current` instead of `overdue`. The full suite was run: **65 tests
ran, 8 failed** —

- `test_compliance.TestCompliance.test_overdue_when_past_due_and_incomplete`
- `test_compliance.TestCompliance.test_derivation_deterministic_in_as_of`
- `test_compliance.TestCompliance.test_in_progress_does_not_complete`
- `test_compliance.TestCompliance.test_list_compliance_derives_each`
- `test_compliance.TestCompliance.test_validation_and_permissions`
- `test_negative_control.TestNegativeControlMutantCompliance.test_past_due_incomplete_is_overdue_canonical_but_mutant_current`
- `test_reporting.TestReporting.test_report_compliance_uses_derived_status`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`f9c8ea1018db3d3ba10fc21bd00a7c592f4adf682d3a23e0fdc6a7417cbd3ffc`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`) and the suite re-run: **65 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.
