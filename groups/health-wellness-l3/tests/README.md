# Tests — Health & Wellness L3-adjacent merged build (FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to.

This suite **extends the shipped Group 18 (Health & Wellness L2)
suite**: the L2 tests were copied and pass with only the minimal
adaptations listed below, and new files cover the High-baseline
uplifts. Per the Merge Rule, the merged fork inherits the higher
tier (High) in full while reusing the Group 18 code (Apache-2.0,
ours) wherever functions overlap.

## Run

```bash
cd groups/health-wellness-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 121 tests
```

Status at delivery: **121 tests, OK** (67 inherited from Group 18,
7 added inside inherited files for the uplifts, 47 in new files).
(Run exactly as above: helpers are imported as a top-level module
from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 12 | Core 9 RBAC — exact permission matrix for admin/clinician/member/auditor (16 actions), `permissions_for()`, `can()`, `require()`, unknown role denied; **[L3]** auditor role tightened to `{audit_read}` only (AC-5, 5 added tests) |
| `test_participants.py` | 6 | Core 1 participant registry — creation shape/provenance with exactly the contract fields, `par-` ids, patient/caregiver/professional kinds, duplicate `participant_ref` rejected with no id consumed, get/list sorted, `participant_write` admin-only, member scope, **no identifier fields exist** |
| `test_programs.py` | 4 | Core 2 program registry — `prg-` shape, program/clinic/care_journey kinds, validation, get/list sorted, `program_write` admin-only, programs readable by admin/clinician/member without scoping; **[L3]** auditor denied |
| `test_enrollments.py` | 5 | Core 3 enrollments with derived status — enrollment + registration kinds, duplicate active enrollment rejected with no id consumed, unknown participant/program, derived precedence overdue > completed > enrolled, plans in other programs ignored, member scope reads, list filters |
| `test_measurements.py` | 5 | Core 4 measurement/outcome records — `msr-` exact field shape, value validation (bool/string/NaN/inf refused; int/float/zero/negative accepted), metric/unit/date validation, unknown refs, **no diagnosis/note field exists**, filters, member scope |
| `test_plans.py` | 5 | Core 5 care/wellness plan records — `pln-` shape with `completed_on` initially None, overdue/current/completed derivation against explicit `as_of` (on-due-date is current; completion before due date allowed), double-complete rejected, kinds, list derives each, member scope |
| `test_activities.py` | 4 | Core 6 activity/appointment records — `act-` records bound to participants/programs, appointment/activity/session kinds, lifecycle states scheduled/completed/cancelled, ends-before-starts/bad kind/malformed datetime validation, filters, member scope |
| `test_eligibility.py` | 4 | Core 7 eligibility/coverage records — `elg-` records under an opaque `plan_ref` only (**no insurer/member-number/benefit fields**), derived upcoming/current/ended incl. boundary dates and open-ended coverage, end-before-start validation, `eligibility_write` admin-only, member scope incl. `eligibility_status` |
| `test_reporting.py` | 5 | Core 8 population scorecard reporting — `report` counts every family with exact contract keys, per-metric count/min/max/mean aggregates, derived plan/eligibility breakdowns at `as_of`, enrollments per program, empty-store shape, member denied `report_read`; `scorecard` program-scoped aggregates + distinct participants, unknown program; **[L3]** auditor denied `report_read` (AC-5) |
| `test_audit.py` | 6 | Core 10 append-only audit log — entry keys (superset incl. [L3] chain fields), User actor normalised, append-only/copies, JSONL persistence + reload (in group `scratch/`), store recording every mutation action, failed ops record nothing, report/scorecard reads audited |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, `verify_chain()`, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` (incl. auditor allowed, clinician/member denied) |
| `test_audit_query.py` | 13 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params, auditor can use the reduced search |
| `test_audit_failure.py` | 6 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, store create/complete roll back in full (no record, no id consumed), service create is not a success |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, success resets counter, lock expiry |
| `test_privacy.py` | 7 | **[L3] Hard privacy rule** — exact key sets per entity (participant/program/enrollment/measurement/plan/activity/eligibility); no entity carries a name/email/phone/dob/diagnosis/note/identifier field; unknown JSON keys refused at the HTTP boundary (400) on participants/programs/plans/eligibility; measurement records refuse extra fields; no record anywhere carries clinical content or a diagnostic field |
| `test_service.py` | 11 | REST API — live HTTP server: health, 401s, 403s audited `:denied`, full flow, privacy boundary (smuggled keys -> 400, nothing stored), member scope over HTTP, `audit_read` admin + auditor, **[L3]** auditor allowed on /audit + /audit/verify / denied on records + /report (1 added test), 400/404 envelopes, DELETE 404 |
| `test_main_cli.py` | 3 | `python -m health serve` subprocess with demo users alice/bob/carol/dana; no-subcommand returns 2; **[L3] +1**: dana=auditor (audit_read only) and `--max-failed-logins` / `--lockout-seconds` |
| `test_negative_control.py` | 4 | Negative control #1 (below), unchanged from Group 18 |
| `health_helpers.py` | — | Shared fixtures: demo users (ADMIN=alice/admin, CLINICIAN=bob/clinician, MEMBER=carol/member, AUDITOR=dana/auditor), `USERS` registry, `fresh_store()`, `make_store()` building a HealthStore + AuditLog + one program ("Diabetes Care") + one participant under opaque ref "carol" (both created by ADMIN). Unchanged from Group 18 |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params (actor/action/since/until, plus target) | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (snapshot), service does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (6 tests) |
| Separation of duties: role `auditor` tightened to `{audit_read}` only (at L2 it also held the 7 record reads + `report_read`); demo user `dana=auditor` unchanged | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py` (5 tests), `test_service.py`, `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 L2 core functions keep their Group 18 coverage (see the
file table); the L3 public API contract is the L2 contract plus
exactly the uplifts above. One deliberate consequence of the AC-5
tightening: endpoints the L2 auditor could read (records,
`/report`, `/scorecard`) are now in practice admin/clinician-only —
the service permission checks still key off actions, not roles,
and the matrix does the rest.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 18): a
   `HealthStore` subclass (`MutantHealthStore`) overriding the
   derivation point — `_derive_plan_status` always returns
   `"current"`. The test asserts the canonical expectations (a
   past-due incomplete plan reads `overdue`, a completed plan reads
   `completed`, and an enrollment over a past-due plan reads
   `overdue`), that the mutant would NOT produce them, and — via a
   literal `assertRaises(AssertionError)` — that treating the
   mutant's outcome as the expected outcome fails. A fourth test
   asserts the companion RBAC gate: a member creating a program is
   denied and the registry stays empty.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field, a rewritten `prev_hash`, and an edited
   JSONL line after reload.

## Mutation verification

The external mutation drills are performed by the coordinator on
the final tree (not by this builder). The drill copies are in the
group `scratch/` directory, byte-identical to the delivered
sources:

- `scratch/store.py.premutation` — SHA-256
  `a0430e37eb414380b1ae9facea3cc1998c74ec0e7a3bba40a03b363047676685`,
  recorded in `scratch/store.py.sha256` (`src/health/store.py`).
- `scratch/audit.py.premutation` — SHA-256
  `be169ca58a5f6a7f000ad670feeeef7e8b56b337ece0ad4b849bf49f5b75895f`,
  recorded in `scratch/audit.py.sha256` (`src/health/audit.py`).

Drill 1 targets the overdue branch of
`HealthStore._derive_plan_status` (the inherited Group 18 control);
Drill 2 targets `AuditLog.verify_chain` [L3]. The Group 18 drill
record for the same derivation point lives in the Group 18 suite's
README.

**Drill results (coordinator, on the final tree, Oct 31, 2026):**

- **Drill 1 — derivation mutant.** The overdue branch of
  `_derive_plan_status` was patched out (an incomplete plan past
  its due date reads `current` instead of `overdue`): the suite
  ran 121 tests with **exactly 8 failures**. `store.py` was then
  restored from `scratch/store.py.premutation` and verified
  byte-identical (`sha256sum -c scratch/store.py.sha256` → OK);
  the suite returned to green (121, OK).
- **Drill 2 — chain-verification mutant.** `verify_chain()` was
  patched to return `(True, None)` unconditionally: the suite ran
  121 tests with **exactly 4 failures** (the tamper-detection
  tests). `audit.py` was restored from
  `scratch/audit.py.premutation` and verified byte-identical
  (`sha256sum -c scratch/audit.py.sha256` → OK); the suite
  returned to green (121, OK).
- **Live tamper check (coordinator smoke, not a patch):** on a
  fresh store, `verify_chain()` reported `(True, None)`; after
  mutating entry 1's actor in place it reported `(False, 1)` —
  the exact index.

## Group 18 test adaptations (complete list)

Every copied Group 18 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — one exact key-set assertion relaxed to
   supersets.** `test_entry_keys_and_actor_normalisation` asserted
   audit entries carry *exactly*
   `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertion now
   requires the original five keys plus the three chain keys as
   subsets. No other audit assertion changed.
2. **`test_access.py` — auditor test rewritten + additive class.**
   `test_auditor_reads_plus_audit_no_writes` now asserts
   `permissions_for("auditor") == {"audit_read"}` (at L2 it asserted
   the 7 record reads + `report_read` + `audit_read`). A new
   `TestAuditorRole` class (5 tests, AC-5) pins the tightened
   matrix, the record/report/write denials, and that the other
   roles' matrices did not move. All other per-role assertions are
   unchanged.
3. **`test_participants.py` — one actor swap.**
   `test_get_list_sorted_and_unknown` read the second participant
   as AUDITOR; the auditor no longer holds `participant_read`, so
   it now reads as CLINICIAN. The write-denial loop
   (clinician/member/auditor) is unchanged — the auditor is still
   denied `participant_write`.
4. **`test_programs.py` — auditor read adaptations.**
   `test_get_list_and_unknown` lists programs as CLINICIAN instead
   of AUDITOR. `test_write_admin_only_reads_open` now loops the
   readable roles (admin/clinician/member) and adds an explicit
   assertion that the auditor is denied `program_read` [L3].
5. **`test_reporting.py` — auditor report adaptations.**
   `test_scorecard_scoped_to_program` reads the scorecard as ADMIN
   instead of AUDITOR. `test_report_permissions` now asserts admin
   and clinician may report and that the auditor is *denied*
   `report_read` [L3], alongside the unchanged member denial.
6. **`test_service.py` — full-flow reader swap + additive only.**
   In `test_full_flow`, the six derived-status/scorecard/report
   reads previously made as DANA (auditor) are now made as BOB
   (clinician, who holds the record reads + `report_read`); all
   assertions are unchanged. One new test
   (`test_audit_read_auditor_allowed_records_denied`) pins that
   dana can use /audit and /audit/verify but gets 403 on
   /programs, /participants and /report. `test_audit_access`
   (admin + auditor 200, clinician + member 403) is unchanged, and
   its auth-failure counts per username stay below the new default
   lockout threshold (max 1 per user), so no lockout trips.
7. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new lockout
   flags and asserts dana can GET /audit but not /programs; the
   original CLI tests are byte-identical.

No other Group 18 test file was modified (`test_activities.py`,
`test_eligibility.py`, `test_enrollments.py`,
`test_measurements.py`, `test_negative_control.py`,
`test_plans.py`, `health_helpers.py` and `tests/__init__.py` are
byte-identical to Group 18).

## Interpretation notes

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic.
- `GET /audit/verify` reads the entry count *before* appending its
  own `audit_read` entry; the endpoint test asserts against the
  pre-request length.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform.
