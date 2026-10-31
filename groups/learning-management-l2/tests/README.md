# Tests — Learning Management L2 singleton build

Stdlib `unittest` only. Every test docstring names the core
function / claim family / control family it traces to.

## Run

```bash
cd groups/learning-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 118 tests
```

Status at delivery: **104 tests, OK** against the implementation
in `../src/`. After the remainder addition (unit
`addition:learning-management-l2`): **118 tests, OK** (see the
additions row in the layout table and the drill re-run record at
the end of this file). (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 8 | Core 13 RBAC — exact permission matrix for admin/instructor/learner/auditor, `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | 5 | Core 14 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording mutation actions, failed ops record nothing |
| `test_learners.py` | 6 | Core 1 learner registry — `lrn-` shape/provenance, duplicate ref rejected with no id consumed, validation, learner_write admin-only |
| `test_catalog.py` | 11 | Core 2 catalog — course/program kinds, all nine content standards accepted + bad standard rejected, lesson-plan reference resolution (unknown ref → NotFoundError), catalog_write admin-only |
| `test_registrations.py` | 13 | Core 3 events & registrations — capacity → waitlist derivation, derived seat view vs. stored record, promotion into a full event rejected, duplicate active registration rejected with no id consumed, re-register after cancellation, learner scope |
| `test_authorizations.py` | 7 | Core 4 SF-182 authorization records — requested → approved/declined flow, **decider ≠ creator** (PermissionDenied), double-decide rejected, validation, learner scope |
| `test_plans.py` | 5 | Core 5 IDP records — shape, activities deep-copied (caller mutation does not reach the store), activity/target-date validation, learner scope |
| `test_competencies.py` | 5 | Core 6 competency records — definitions, learner levels recorded **verbatim**, unknown learner/competency, learner scope |
| `test_progress.py` | 4 | Core 7 progress records — shape, status/readiness/percent validation (bool percent rejected), unknown learner/course, learner scope |
| `test_statements.py` | 5 | Core 8 LRS statement records — **exact eight-key shape**, `result_text` stored verbatim (a "score: 88/100" string stays a string), recursive **no-score-field pin** across statement/progress/learner-competency/report shapes |
| `test_compliance.py` | 8 | Core 9 compliance — stored record carries **no status field**, current/overdue/completed derivation against explicit `as_of`, on-due-date is current, completion overrides overdue, in_progress does not complete, derivation deterministic in `as_of`, compliance_write admin-only, learner scope |
| `test_workflows_notifications.py` | 6 | Core 10 registries — workflow definitions validated, **never-executes pin** (registering a workflow changes no registration/authorization/notification state), notification records + recipient filter |
| `test_reporting.py` | 7 | Core 11 search & reporting — empty-store shape, populated counts, compliance counts use derived status at `as_of`, substring search, learner denied `report_read` (search and report) |
| `test_service.py` | 10 | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (learner → course → content → lesson plan → event → register → authorization decided by a different actor → IDP → competency → progress → statement → compliance derived overdue → completed → report → search), learner write 403 + denied audited, learner scope over HTTP, audit admin+auditor only, 400/404 envelopes |
| `test_main_cli.py` | 1 | `python -m lms serve` subprocess with demo users alice/bob/carol/dana |
| `test_negative_control.py` | 3 | Negative control (below) |
| `test_additions.py` | 14 | Remainder addition (unit `addition:learning-management-l2`) — spec integrity for the appended Percipio sheet (count/order/membership, the original claim table standing at 26, the literal **zero-claim** table and whole-taxonomy zero-claim set, tier fields, verbatim description, census citation accounting, exclusion-segment pin, named-absence rechecks, near-miss pins) + 2 substrate cases (progress record with compliance status derived at read; catalogue content records with an exact-eight-key statement and recursive no-score scan) |
| `lms_helpers.py` | — | Shared fixtures: demo users (ADMIN/INSTRUCTOR/LEARNER/AUDITOR), `USERS` registry, `fresh_store()`, and `make_store()` building an LmsStore + AuditLog + one learner (ref `carol`) + one course |

## Negative control

`test_negative_control.py` implements the contract's negative
control: an `LmsStore` subclass (`MutantLmsStore`) whose
`_derive_status` always returns `"current"` — the compliance
status derivation is skipped. The traced claim, named in the
module's docstrings, is that **compliance status is derived
deterministically from assignment, due date, and progress
records**: a past-due incomplete assignment must read `overdue`,
and an assignment with a completed progress record must read
`completed`. For each canonical case (past-due incomplete,
completed) the test asserts three things: the canonical
expectation (from the real implementation), that the mutant would
NOT produce that expectation (it says `current` anyway), and —
via a literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails. A third test
asserts the companion RBAC gate: a learner creating a compliance
assignment is denied and nothing is stored.

## Mutation verification

VERIFIED by the coordinator for this group (2026-10-31). The
overdue branch in `LmsStore._derive_status` (`src/lms/store.py`) —
the line `return "overdue"` under `if as_of_date > due:` — was
patched to `return "current"`, the exact live counterpart of the
mutant in `test_negative_control.py`, so a past-due incomplete
assignment read `current` instead of `overdue`. The full suite
was run: **104 tests ran, 9 failed** (raw output in
`scratch/mutation-run.txt`) —

- `test_compliance.TestCompliance.test_completed_progress_overrides_overdue`
- `test_compliance.TestCompliance.test_derivation_deterministic_in_as_of`
- `test_compliance.TestCompliance.test_in_progress_does_not_complete`
- `test_compliance.TestCompliance.test_list_compliance_derives_each`
- `test_compliance.TestCompliance.test_overdue_when_past_due_and_incomplete`
- `test_compliance.TestCompliance.test_validation_and_permissions`
- `test_negative_control.TestNegativeControlMutantCompliance.test_past_due_incomplete_is_overdue_canonical_but_mutant_current`
- `test_reporting.TestReporting.test_report_compliance_uses_derived_status`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from the pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`820d97121fd55799b77b417b23d72d26680e22596141ee58e52cfa32bb3bba8a`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`) and the suite re-run: **104 tests,
OK**. The suite catches this defect class; the negative control
is not decorative.

## Remainder addition — drill re-run (unit `addition:learning-management-l2`)

The addition changes no core code (`src/` byte-identical, all 7
`lms` module hashes verified against the pre-work baseline in
`../scratch/additions_src_hashes_before.txt`), so the group's
signature drill was re-run in this tree against the enlarged
suite (118 tests). Raw output in
`../scratch/additions_mutation_run.txt`.

**Drill re-run — compliance derivation.** The overdue branch of
`LmsStore._derive_status` in `src/lms/store.py` (`return
"overdue"` under `if as_of_date > due:`) was patched to `return
"current"` — the same scoped patch as the original drill (the
branch text occurs exactly once in the file, count asserted
before patching). The full suite ran: **118 tests, exactly 10
failures** — the shipped drill's identical 9 plus exactly 1 from
the additions module,
`test_additions.TestAdditionSubstrateCases.test_percipio_progress_and_compliance_derivation`,
tripping on the mutant exactly as designed. `store.py` was
restored from `../scratch/store.py.premutation-additions` and
verified SHA-256-identical to the shipped hash (`820d9712…`);
the suite re-ran green: **118 tests, OK**.
