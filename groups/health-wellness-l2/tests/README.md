# Tests — Health & Wellness L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim family / control family it traces to.

## Run

```bash
cd groups/health-wellness-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 91 tests
```

Status at delivery: **67 tests, OK** against the implementation in
`../src/`; **80 tests, OK** after the remainder additions
(`test_additions.py`, see `../ADDENDUM.md`); **91 tests, OK** after
the no-signal addition (`test_nosignal_addition.py`, see
`../ADDENDUM.md` section 7). (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/clinician/member/auditor (16 actions), `permissions_for()`, `can()`, `require()`, unknown role denied. RBAC is baseline-carried, not claimed (0/5) |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload with malformed-line skip (in group `scratch/`), store recording each mutation action, failed ops record nothing, report/scorecard reads audited. Carried-not-claimed (0/5) |
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
| `test_additions.py` | Remainder additions (unit `addition:health-wellness-l2`) — spec integrity: the unit's slice of the sheets, the first 8 in order (5 shipped + 3 appended in census unit order; a 9th, no-signal, sheet follows — pinned in `test_nosignal_addition.py`), membership against `remainder.json`, the literal **zero-claim** table for all 3 additions (taxonomy verbatim; group total stays 19), tier fields, descriptions verbatim against the cached dataset, 4/4 census citations as substrings (verification ≠ claim), per-fork near-miss pins (substance token present, family phrase absent). Plus one substrate case per fork: GTS telehealth visit as a Core 6 activity record with exact key set (no media field) + Core 4 monitoring measurement + plan/enrollment deriving overdue; Solventum Core 7 coverage record under opaque `plan_ref` deriving upcoming → current → ended with exact key set (no insurer/member fields); Somnoware Core 5 CPAP plan deriving current → overdue → completed over a Core 4 measurement with no diagnosis field |
| `test_nosignal_addition.py` | No-signal addition (`FR2220549818`, CirrusMD) — spec integrity: 9 sheets in order, the 8 shipped sheets deep-equal to git HEAD, membership against the census `no-signal-set` (citations [], no_signal pinned), the literal **zero-claim** table for the fork (taxonomy verbatim; group total stays 19; 4 of 9 forks at zero), tier fields, description verbatim against both cached sources (raw dataset and `remainder/uncovered.json`), the classification citation pinned against `remainder/nosignal_report.json` (verbatim sentence + URL; asserted NOT present in the cached description — classification ≠ claim evidence), near-miss pins (delivery/posture tokens present, all family phrases absent, the word "patient" absent). Plus one substrate case: CirrusMD virtual health chat visit as a Core 6 activity record with exact key set (no channel/message field) + follow-up plan and enrollment deriving overdue |
| `health_helpers.py` | Shared fixtures: demo users (ADMIN=alice/admin, CLINICIAN=bob/clinician, MEMBER=carol/member, AUDITOR=dana/auditor), `USERS` registry, `fresh_store()`, and `make_store()` building a HealthStore + AuditLog + one program ("Diabetes Care") + one participant under opaque ref "carol" (both created by ADMIN) |

## Negative control

`test_negative_control.py` implements the contract's negative
control: a `HealthStore` subclass (`MutantHealthStore`) whose
`_derive_plan_status` always returns `"current"` — the derived-status
derivation is skipped. The traced claim, named in the module's
docstrings, is that **plan status is derived deterministically from
due/completion dates, and enrollment status is derived from the
participant's plan records**: a past-due incomplete plan must read
`overdue`, a completed plan must read `completed`, and an enrollment
over a past-due incomplete plan must read `overdue`. For each
canonical case (past-due incomplete plan, completed plan, enrollment
over a past-due plan) the test asserts three things: the canonical
expectation (from the real implementation), that the mutant would
NOT produce that expectation (it says `current` for plans, and the
enrollment consequently reads `enrolled`), and — via a literal
`assertRaises(AssertionError)` — that treating the mutant's outcome
as the expected outcome fails. A fourth test asserts the companion
RBAC gate: a member creating a program is denied and the registry
stays empty.

## Mutation verification

VERIFIED by the build worker (2026-10-25). The overdue branch in
`HealthStore._derive_plan_status` (`src/health/store.py`) — the line
`return "overdue"` under `if as_of_date > due:` — was patched to
`return "current"`, the exact live counterpart of the mutant in
`test_negative_control.py`, so a past-due incomplete plan read
`current` instead of `overdue` (and its enrollment read `enrolled`).
The full suite was run: **67 tests ran, 8 failed** —

- `test_enrollments.TestEnrollments.test_derived_completed_and_overdue_precedence`
- `test_plans.TestPlans.test_derived_overdue_current_completed`
- `test_plans.TestPlans.test_list_derives_each_and_member_scope`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_past_due_incomplete_plan_is_overdue_canonical_but_mutant_current`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_enrollment_overdue_follows_plan_canonical_but_mutant_enrolled`
- `test_reporting.TestReporting.test_report_counts_and_aggregates`
- `test_reporting.TestScorecard.test_scorecard_scoped_to_program`
- `test_service.TestFullFlow.test_full_flow`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`,
verified identical to the pre-mutation hash in
`scratch/store.py.sha256`) and the suite re-run: **67 tests, OK**.
The suite catches this defect class; the negative control is not
decorative.

**Additions re-run (remainder unit `addition:health-wellness-l2`).**
The core is unchanged by the additions, so the same drill was
re-run in this tree: the overdue branch of `_derive_plan_status`
patched to `return "current"`, full suite run — **80 tests,
exactly 10 failures**: the original drill's 8 above plus 2 from
`test_additions.py`
(`test_gts_telehealth_visit_is_an_activity_record`,
`test_somnoware_cpap_plan_and_measurement_shapes`), which derive
plan/enrollment status and trip exactly as designed; the Solventum
coverage case does not depend on plan derivation and did not trip.
Raw output in `scratch/additions_mutation_run.txt`. `store.py` was
restored from `scratch/store.py.premutation-additions` and verified
SHA-256-identical to the shipped hash
(`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`);
the suite re-ran green: **80 tests, OK**.

**No-signal addition re-run (2026-10-31, fork `FR2220549818`).** The
core is again unchanged, so the same drill was re-run in this tree:
the overdue branch of `_derive_plan_status` patched to
`return "current"`, full suite run — **91 tests, exactly 11
failures**: the additions re-run's 10 above plus 1 from
`test_nosignal_addition.py`
(`test_cirrusmd_chat_visit_is_an_activity_record`), which derives
plan/enrollment status and trips exactly as designed. Raw output in
`scratch/nosignal_mutation_run.txt`. `store.py` was restored from
`scratch/store.py.premutation-nosignal` and verified
SHA-256-identical to the shipped hash
(`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`);
the suite re-ran green: **91 tests, OK**, with `src/` byte-identical
including the tracked bytecode.
