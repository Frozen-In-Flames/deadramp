# Tests — Construction L2 merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

## Run

```bash
cd groups/construction-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 146 tests
```

Status at delivery: **146 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers |
|---|---|
| `test_access.py` | Access control (RBAC) — exact permission matrix for admin/operator/viewer (17 actions), `permissions_for()`, `can()`, `require()`, unknown role/action denied |
| `test_audit.py` | Append-only audit log — entry keys, User actor normalised to name, append-only/copies, JSONL persistence + reload on construction (in group `scratch/`), store recording every contract mutation action name, failed ops record nothing |
| `test_projects_orgs.py` | Organizations + projects + participants — `org-`/`prj-` creation shape/provenance/defaults, copies-are-copies, validation, project lifecycle (planned→active→on_hold→completed→closed, cancel paths) + invalid transitions, list status filter, participants (tier int ≥ 1 with bool/float/0/negative/string rejected, duplicate org → `ValidationError`, unknown ids → `NotFoundError`, sort by (tier, org number)), no-id-on-failure |
| `test_documents.py` | Documents — `doc-` creation at version 1 (`{version, checksum, note, ts}`, record mirrors current fields), all `DOC_TYPES`, update appends versions carrying the unchanged field forward, update with neither field → `ValidationError`, bad doc_type / unknown project, copies-are-copies, project filter |
| `test_contracts.py` | Contracts — `con-` creation validation (money rule on `value_cents`: float/bool/negative/string rejected; `key_dates` label/at validation + deep copies; unknown project/org), full lifecycle + review→draft + terminations + invalid transitions, expiry derivation via `_contract_expiry_state` (pre_execution, open_ended, active, expiring within 30 days incl. the 30-day edge, expired, ended; `days_to_expiry` sign incl. negative), derived-not-stored, list filters, no-id-on-failure |
| `test_records.py` | Submittals + RFIs — `sub-` lifecycle incl. revise_resubmit loop and approved/approved_as_noted/rejected terminals + guards, `rfi-` lifecycle incl. answered→open reopen and closed terminal, overdue derivation via `_record_overdue` (past-due non-terminal overdue; future/no-due not; terminal statuses never overdue), list filters |
| `test_schedule.py` | Milestones + dispatches — `ms-` due-state derivation via `_milestone_due_state` (upcoming / due_soon within 7 days incl. edges / overdue / completed-wins), `due_at` required, complete guards (double complete → `ValidationError`, default `completed_at`), derived-not-stored; `dsp-` lifecycle assigned→in_progress→completed/cancelled + invalid transitions |
| `test_inspections.py` | Inspections + punch items — `insp-` creation, result validation (pass/fail/conditional/None), immutability (no update/transition API on the store); `pun-` lifecycle open→corrected→verified with corrected→open reopen, overdue derivation (open/corrected overdue, verified never), inspection/org reference checks |
| `test_incidents.py` | Incidents — `inc-` creation with all severities (info/warning/critical, default info), severity/category/description validation, lifecycle reported→under_review→closed with under_review→reported return path, transition guards, list filters |
| `test_workforce.py` | Workforce — `wrk-` opaque reference required (never a real government identifier), `time-` entries (minutes int > 0, bool/float/zero/negative rejected, worker must exist, immutability, project filter through the worker), `pay-` payrolls (period end < start rejected, `certified` must be bool, worker_count + money rules, immutability), `vio-` violations (**operator and viewer create → `PermissionDenied`**, violation_write is admin-only; resolve only from open), compliance derivation via `_contractor_compliance` (no_records with nothing; compliant after a certified payroll; still no_records after an uncertified payroll; noncompliant with an open violation even with a certified payroll; back to compliant after resolve; pairs independent) |
| `test_costs.py` | Costs — `cost-` entries, money rule on both amount fields, kind validation (`COST_KINDS`), immutability, list filters, `project_cost_summary` sums (None counts 0) and variance (budgeted − actual), empty-project summary zeros, per-project scoping |
| `test_alerts_reports_search.py` | Derived alerts + report + search — each alert kind produced deterministically (contract_expired/contract_expiring, milestone_overdue, submittal_overdue, rfi_overdue, punch_overdue, compliance_noncompliant, compliance_no_records) and sorted by (kind, ref_id), now-dependence; report shape/counts incl. compliance counts over participants, cost totals, and now-dependence of expiry counts; search shape `{projects, organizations, documents, contracts}`, name/reference/title matching, contract views carry derived expiry, literal-not-regex, empty query → `ValidationError` |
| `test_service.py` | REST API — live HTTP server: health, 401 unknown user / role mismatch, 403 viewer write + operator violation create (denied attempts audited with `:denied`), full flow across the main entities (org → project + participants → document create/PATCH → contract lifecycle with `?now=` expiry → submittal/RFI/milestone/dispatch/inspection/punch/incident → worker/time-entry/payroll → violation + compliance endpoint → costs + cost-summary → alerts/report/search → audit), compliance without `org_id` → 400, `audit_read` admin-only, 400/404 envelopes |
| `test_main_cli.py` | `python -m construct serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `construct_helpers.py` | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER), `USERS` registry, `fresh_store()`, and `make_store()` building a ConstructStore + AuditLog + an active project + a prime org (tier 1 participant) + a sub org (tier 2 participant), all created by ADMIN |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a `ConstructStore` subclass (`MutantConstructStore`) overriding the
two derivation points — `_contractor_compliance` always returns
`"compliant"` and `_contract_expiry_state` always returns `"active"`.
The traced claims, named in the module's docstrings, are that
**compliance and expiry derivation happen at read time**: (a) a
participant with an open violation must read `noncompliant`, (b) a
participant with nothing must read `no_records`, and (c) an executed
contract past its `end_at` must read `expiry_state='expired'`. For
each canonical case the test asserts three things: the canonical
expectation (derived value from the real implementation, including
the report counts), that the mutant would NOT produce that
expectation (it reads compliant / compliant / active), and — via a
literal `assertRaises(AssertionError)` — that treating the mutant's
outcome as the expected outcome fails.

## Mutation verification

VERIFIED by the builder (2026-10-25), live drill performed on the
real implementation (not just the subclass mutant). The body of
`ConstructStore._contractor_compliance` (`src/construct/store.py`) —
THE load-bearing derivation point for contractor compliance — was
patched to `return "compliant"`, the exact live counterpart of the
mutant in `test_negative_control.py`, so a participant with an open
violation never read noncompliant and a participant with no records
never read no_records. The full suite was run: **146 tests ran,
11 failed** —

- `test_alerts_reports_search.TestAlerts.test_compliance_no_records_for_bare_participants`
- `test_alerts_reports_search.TestAlerts.test_each_alert_kind`
- `test_alerts_reports_search.TestReport.test_report_shape_and_counts`
- `test_negative_control.TestNegativeControlMutantDerivation.test_no_records_canonical_but_mutant_not`
- `test_negative_control.TestNegativeControlMutantDerivation.test_open_violation_noncompliant_canonical_but_mutant_not`
- `test_service.TestFullFlow.test_full_flow`
- `test_workforce.TestCompliance.test_back_to_compliant_after_resolve`
- `test_workforce.TestCompliance.test_no_records_with_nothing`
- `test_workforce.TestCompliance.test_noncompliant_with_open_violation_even_with_certified_payroll`
- `test_workforce.TestCompliance.test_pairs_are_independent`
- `test_workforce.TestCompliance.test_uncertified_payroll_still_no_records`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`49b5b203bd6dfece596aafed6987b06d7f7c9574efd047669026afa6a5cd7d65`,
recorded in `scratch/store.py.sha256` and verified identical after
restore) and the suite re-run: **146 tests, OK**. The suite catches
this defect class; the negative control is not decorative.
