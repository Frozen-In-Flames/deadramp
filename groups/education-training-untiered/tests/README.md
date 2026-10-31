# Tests — Education & Training untiered set

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/education-training-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 74 tests
```

Status at delivery: **74 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

The core suite is the founding group's (Education & Training L2,
Group 13) suite carried with the code — 65 tests — minus its
`test_additions.py`, which pins a different census unit
(`addition:education-training-l2`) and is not carried. One labeling
fix: `learn_helpers.py`'s docstring now names this untiered set
instead of L2. Added here: `test_specs.py` (9 tests).

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/instructor/learner/auditor, `permissions_for()`, `can()`, `require()`, unknown role denied |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload (in group `scratch/`), store recording each mutation action, failed ops record nothing |
| `test_courses.py` | Core 1 course/catalog registry — creation shape/provenance, `crs-` ids, course vs program kinds, get/list sorted, validation, catalog_write admin-only, unknown id |
| `test_enrollments.py` | Core 2 enrollments & registrations — enrollment + registration kinds, duplicate active enrollment rejected with no id consumed, unknown course, learner write denied, learner scope reads, list filters |
| `test_progress.py` | Core 3 progress & readiness records — `prg-` shape, readiness/percent, completion as terminal state record, validation (bad status/readiness/percent, unknown course), learner scope |
| `test_assessments.py` | Core 4 assessment records — `asm-` administration records, item responses stored verbatim with **no score/grade field** (the founding doctrine: scoring is Extended), duplicate item rejected, state transitions, session binding, learner scope |
| `test_credentials.py` | Core 5 credential records — `cred-` records with ISO issued/expiry dates, status update as record change, date validation, credential_write admin-only, learner scope. Records only; no issuance |
| `test_compliance.py` | Core 6 compliance assignments & derived status — stored record carries **no status field**, overdue/current/completed derivation against explicit `as_of`, on-due-date is current, completion overrides overdue, in_progress does not complete, derivation deterministic in `as_of`, admin-only writes, learner scope |
| `test_scheduling.py` | Core 7 scheduling records — `sch-` training/assessment sessions bound to courses and learner ids, assessment record referencing a session, ends-before-starts/bad kind/malformed datetime validation, role gates |
| `test_reporting.py` | Core 8 reporting — counts over all record families, per-status breakdowns, enrollments by course, report compliance counts use derived status at `as_of`, learner denied `report_read`, empty-store shape |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (course → enroll → session → assessment + response → credential → compliance derived overdue → progress completed → derived completed → report), learner write 403 + denied audited, learner scope over HTTP (403 on another learner's enrollment), audit admin+auditor only, report learner 403, 400/404 envelopes |
| `test_main_cli.py` | `python -m learn serve` subprocess with demo users alice/bob/carol/dana |
| `test_negative_control.py` | Negative control (below) |
| `test_specs.py` | Untiered spec integrity — exactly 6 sheets; membership exact against remainder.json unit `untiered:Education & Training`; tier discipline on every sheet (`cmmc_tier` null, impact "Unknown"); every claim's evidence verbatim in its description (under the founding `\r`→space normalization, stated in the test); literal totals (29 claims, zero-claim set exactly {FR1916744879}); the exact per-fork claim table; the exclusion-pass pins (no claim evidence carries scope-exclusion phrasing; Toonimo's removed certification hit stays removed) |
| `learn_helpers.py` | Shared fixtures: demo users (ADMIN/INSTRUCTOR/LEARNER/AUDITOR), `USERS` registry, `fresh_store()`, and `make_store()` building a LearnStore + AuditLog + one course (created by ADMIN) |

## Negative control

`test_negative_control.py` is carried from the founding group
unchanged: a `LearnStore` subclass (`MutantLearnStore`) whose
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

## Mutation verification — the founding group's signature drill, re-run in this tree

VERIFIED for this build (2026-10-31). The founding group's recorded
signature drill is the compliance-derivation mutation: the overdue
branch in `LearnStore._derive_status` (`src/learn/store.py`) — the
line `return "overdue"` under `if as_of_date > due:` (line 615; the
named line occurs exactly once in the file, count asserted before
patching) — was patched to `return "current"`, the exact live
counterpart of the mutant in `test_negative_control.py`, so a
past-due incomplete assignment read `current` instead of `overdue`.
The full suite was run: **74 tests ran, exactly 8 failed** — the
founding drill's identical failure set (the founding tree's later
additions re-run showed a 9th failure from its `test_additions.py`,
which pins a different census unit and is not carried here; no spec
test failed under the mutant):

- `test_compliance.TestCompliance.test_overdue_when_past_due_and_incomplete`
- `test_compliance.TestCompliance.test_derivation_deterministic_in_as_of`
- `test_compliance.TestCompliance.test_in_progress_does_not_complete`
- `test_compliance.TestCompliance.test_list_compliance_derives_each`
- `test_compliance.TestCompliance.test_validation_and_permissions`
- `test_negative_control.TestNegativeControlMutantCompliance.test_past_due_incomplete_is_overdue_canonical_but_mutant_current`
- `test_reporting.TestReporting.test_report_compliance_uses_derived_status`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from the pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`f9c8ea1018db3d3ba10fc21bd00a7c592f4adf682d3a23e0fdc6a7417cbd3ffc`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256` and to the founding group's shipped
`store.py`) and the suite re-run: **74 tests, OK**. The raw failure
list is in `scratch/mutation_run.txt`. The suite catches this defect
class; the negative control is not decorative.

## Byte-identity accounting (tests)

The carried test files are byte-identical to the founding group's
except `learn_helpers.py` (docstring labeling fix, above) and the
founding additions module, which is not carried; `test_specs.py` is
new. The implementation accounting (7 of 7 `src/learn/` modules
byte-identical to the founding group) is in the group README.
