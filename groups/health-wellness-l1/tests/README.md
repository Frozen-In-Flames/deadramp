# Tests — Health & Wellness L1 singleton build

Stdlib `unittest` only. Every test docstring names the core
function / claim family / control family it traces to. The suite
is Group 18's (Health & Wellness L2), reused: 13 of the 15 carried
test files are byte-identical to Group 18's, and the 2 differing
files differ in documentation wording only (see
`../scratch/reuse-note.md`). Group 18's `test_additions.py` is not
carried — it pins the parent group's remainder additions, not this
singleton. No test logic changed. What the suite verifies does not
change with the tier — the carried substrate's behavior is
identical; what changes at L1 is the baseline the behavior is
claimed against (UNION-SPEC.md), not the code. One new file
(`test_singleton_spec.py`) pins this singleton's spec sheet and
runs four substrate cases in the fork's shape.

## Run

```bash
cd groups/health-wellness-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 79 tests
```

Status at delivery: **79 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_singleton_spec.py` | **This singleton** — spec integrity: single sheet == census unit membership, taxonomy verbatim (ast-parsed from Group 18's extractor) reproducing Group 18's ORIGINAL shipped claim tables exactly (19 claims), the literal **zero-claim** table for the fork (all 11 families at 0, recomputed), tier fields (LI-SaaS recorded as-is, never rounded to Low), description == cached source verbatim, census citation verifies and tags nothing (verification ≠ claim), no-exclusion accounting (certified_services empty; per-sentence hit map all-empty), near-miss pins (substance tokens present, family phrases absent, telehealth/audit/access tokens at zero). Plus 4 substrate cases in the fork's shape: a home sleep-study session as a Core 6 activity record with the exact contract key set (no diagnosis/result/device-data field), a study-administration value as a Core 4 measurement, a Core 7 coverage record under an opaque `plan_ref` deriving upcoming → current → ended, and member scope over those records |
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/clinician/member/auditor (16 actions), `permissions_for()`, `can()`, `require()`, unknown role denied. RBAC is baseline-carried, not claimed (0 claims in category text at any tier). At this tier the auditor keeps Group 18's read set — Singleton 46's High-tier tightening to `audit_read` only is not inherited |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload with malformed-line skip (in group `scratch/`), store recording each mutation action, failed ops record nothing, report/scorecard reads audited. Carried-not-claimed; traced at AU-2/AU-3 on the FedRAMP Low side |
| `test_participants.py` | Core 1 participant registry — creation shape/provenance with exactly the contract fields, `par-` ids, patient/caregiver/professional kinds, duplicate `participant_ref` rejected with no id consumed, get/list sorted, `participant_write` admin-only, member scope, **no identifier fields exist** |
| `test_programs.py` | Core 2 program registry — `prg-` shape, program/clinic/care_journey kinds, validation, get/list sorted, `program_write` admin-only, programs readable by all roles without scoping |
| `test_enrollments.py` | Core 3 enrollments with derived status — enrollment + registration kinds, duplicate active enrollment rejected with no id consumed, unknown participant/program, derived precedence overdue > completed > enrolled, plans in other programs ignored, member scope reads, list filters |
| `test_measurements.py` | Core 4 measurement/outcome records — `msr-` exact field shape, value validation (bool/string/NaN/inf refused; int/float/zero/negative accepted), metric/unit/date validation, unknown refs, **no diagnosis/note field exists**, filters, member scope |
| `test_plans.py` | Core 5 care/wellness plan records — `pln-` shape with `completed_on` initially None, overdue/current/completed derivation against explicit `as_of` (on-due-date is current; completion before due date allowed), double-complete rejected, kinds, list derives each, member scope |
| `test_activities.py` | Core 6 activity/appointment records — `act-` records bound to participants/programs, appointment/activity/session kinds, lifecycle states scheduled/completed/cancelled, ends-before-starts/bad kind/malformed datetime validation, filters, member scope |
| `test_eligibility.py` | Core 7 eligibility/coverage records — `elg-` records under an opaque `plan_ref` only (**no insurer/member-number/benefit fields**), derived upcoming/current/ended incl. boundary dates and open-ended coverage, end-before-start validation, `eligibility_write` admin-only, member scope incl. `eligibility_status` |
| `test_reporting.py` | Core 8 population scorecard reporting — `report` counts every family with exact contract keys, per-metric count/min/max/mean aggregates, derived plan/eligibility breakdowns at `as_of`, enrollments per program, empty-store shape, member denied `report_read`; `scorecard` program-scoped aggregates + distinct participants, unknown program, member denied |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, full flow (program → participant → enroll → measurement → plan derived overdue → activity → eligibility status → complete → derived completed → scorecard + report; member reads own enrollment), **privacy boundary: smuggled `diagnosis`/`note`/`name`/`dob`/`member_number` keys -> 400 and nothing stored**, member write 403 + denied audited, member scope over HTTP (403 on another participant's enrollment), audit admin+auditor only, report member 403, 400/404 envelopes, DELETE 404 |
| `test_main_cli.py` | `python -m health serve` subprocess with demo users alice/bob/carol/dana; no-subcommand returns 2 |
| `test_negative_control.py` | Negative control (below) |
| `health_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, CLINICIAN=bob/clinician, MEMBER=carol/member, AUDITOR=dana/auditor), `USERS` registry, `fresh_store()`, and `make_store()` building a HealthStore + AuditLog + one program ("Diabetes Care") + one participant under opaque ref "carol" (both created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's negative
control: a `HealthStore` subclass (`MutantHealthStore`) whose
`_derive_plan_status` always returns `"current"` — the
derived-status derivation is skipped. The traced claim, named in
the module's docstrings, is that **plan status is derived
deterministically from due/completion dates, and enrollment status
is derived from the participant's plan records**: a past-due
incomplete plan must read `overdue`, a completed plan must read
`completed`, and an enrollment over a past-due incomplete plan
must read `overdue`. For each canonical case (past-due incomplete
plan, completed plan, enrollment over a past-due plan) the test
asserts three things: the canonical expectation (from the real
implementation), that the mutant would NOT produce that
expectation (it says `current` for plans, and the enrollment
consequently reads `enrolled`), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails. A fourth test asserts the
companion RBAC gate: a member creating a program is denied and
the registry stays empty.

## Mutation verification

VERIFIED by the builder in THIS tree (the L1 singleton's tree).
The overdue branch in `HealthStore._derive_plan_status`
(`src/health/store.py`) — the line `return "overdue"` under
`if as_of_date > due:` — was patched to `return "current"`, the
exact live counterpart of the mutant in
`test_negative_control.py`, so a past-due incomplete plan read
`current` instead of `overdue` (and its enrollment read
`enrolled`). The full suite was run: **79 tests ran, exactly 8
failed** — the identical failure set to Group 18's original drill
(the singleton spec file's cases are designed not to touch the
plan derivation, and none tripped):

- `test_enrollments.TestEnrollments.test_derived_completed_and_overdue_precedence`
- `test_plans.TestPlans.test_derived_overdue_current_completed`
- `test_plans.TestPlans.test_list_derives_each_and_member_scope`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_past_due_incomplete_plan_is_overdue_canonical_but_mutant_current`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_enrollment_overdue_follows_plan_canonical_but_mutant_enrolled`
- `test_reporting.TestReporting.test_report_counts_and_aggregates`
- `test_reporting.TestScorecard.test_scorecard_scoped_to_program`
- `test_service.TestFullFlow.test_full_flow`

Raw output in `scratch/mutation_run.txt`. `store.py` was then
restored from the pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256` — and to Group 18's shipped hash, the
source being byte-identical) and the suite re-run: **79 tests,
OK**. The suite catches this defect class; the negative control
is not decorative.
