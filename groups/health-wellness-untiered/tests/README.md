# Tests — Health & Wellness untiered set

Stdlib `unittest` only. The core suite is the founding group's
(Health & Wellness L2) suite carried with the code — the founding
suite minus its `test_additions.py`, which pins a different census
unit — plus `test_specs.py`, new here. One labeling fix in
`health_helpers.py` (its docstring now names this untiered set
instead of the founding group); every other carried test file is
byte-identical to the founding group's. Carried test docstrings
that name the founding contract describe the code's provenance;
at tier null the substrate is carried, not claimed, and the
group README re-anchors it.

## Run

```bash
cd groups/health-wellness-untiered
PYTHONPATH=src python3 -m unittest discover -s tests        # 80 tests
```

Status at delivery: **80 tests, OK** — 67 carried core tests plus
13 spec tests. (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py`
is empty by design, so package-mode discovery with `-t .` is not
the supported entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Core 9 RBAC — exact permission matrix for admin/clinician/member/auditor (16 actions), `permissions_for()`, `can()`, `require()`, unknown role denied. Carried-not-claimed in this set |
| `test_audit.py` | Core 10 append-only audit log — entry keys, User actor normalised to name, append-only/copies, no mutation API, JSONL persistence + reload with malformed-line skip (in group `scratch/`), store recording each mutation action, failed ops record nothing, report/scorecard reads audited. Carried-not-claimed in this set |
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
| `test_specs.py` | This set's spec pins — exactly 3 sheets; membership exact against census unit `untiered:Health & Wellness` in `remainder.json`; every sheet's tier null / impact "Unknown"; registry fields and descriptions verbatim against `forks.json` and the census record; the literal claim table (**1 claim total**: 86Borders `patient_engagement`; Elvo and WellHive zero-claim, named); every claim's evidence verbatim in its description; near-miss pins (WellHive EHR-integration substance not claimed, AWS hosting prose not claimed by either fork, Elvo session metrics not `clinical metrics`, 86Borders "quality scores" not `scorecards`); WellHive's "FedRAMP Moderate authorization" prose pinned as not moving its recorded impact or tier |
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

VERIFIED for this tree (2026-10-31). The founding group's signature
drill was re-run here: the overdue branch in
`HealthStore._derive_plan_status` (`src/health/store.py`, line 282)
— `return "overdue"` under `if as_of_date > due:` — was patched to
`return "current"`, the exact live counterpart of the mutant in
`test_negative_control.py`, so a past-due incomplete plan read
`current` instead of `overdue` (and its enrollment read `enrolled`).
The full suite was run: **80 tests ran, exactly 8 failed** — the
founding drill's identical failure set (no spec test failed):

- `test_enrollments.TestEnrollments.test_derived_completed_and_overdue_precedence`
- `test_plans.TestPlans.test_derived_overdue_current_completed`
- `test_plans.TestPlans.test_list_derives_each_and_member_scope`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_past_due_incomplete_plan_is_overdue_canonical_but_mutant_current`
- `test_negative_control.TestNegativeControlMutantDerivedStatus.test_enrollment_overdue_follows_plan_canonical_but_mutant_enrolled`
- `test_reporting.TestReporting.test_report_counts_and_aggregates`
- `test_reporting.TestScorecard.test_scorecard_scoped_to_program`
- `test_service.TestFullFlow.test_full_flow`

Raw output in `scratch/mutation_run.txt`. `store.py` was then
restored from the pre-mutation copy (`scratch/store.py.premutation`;
SHA-256
`c83cd2d269cb08c5d259d7fc1b16f7d8a761df006e0e9e3889daa4d5c928c711`,
identical to the founding group's shipped hash and to the
pre-mutation hash in `scratch/store.py.sha256`) and the suite
re-run: **80 tests, OK**. The suite catches this defect class; the
negative control is not decorative.
