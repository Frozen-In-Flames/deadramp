# Tests — custsvc (Group 27: Customer Service, L2)

Run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**69 tests, all passing** (Python stdlib `unittest` only, zero
third-party dependencies).

The test files are Group 26's suite reused byte-identical (14 of 14
files SHA-256-identical to `groups/customer-service-l1/tests/`),
because the implementation they test is byte-identical too. The
suite was re-run in full from this directory, and this group's
mutation drill and restore were performed against this directory's
own copy (record below).

## Coverage map

| File | Covers |
|---|---|
| `test_access.py` | Core 10 — RBAC matrix: admin ⊇ all; agent writes cases/requesters/responders/alerts/schedules but NOT rules or audit; viewer read-only, no audit. Unknown roles denied. |
| `test_audit.py` | Core 10 — append-only audit: entry shape/order, no update/delete API exists, store mutations recorded with actor names. |
| `test_requesters.py` | Core 2 — requester privacy is structural: exact record key set pinned, no contact fields exist, duplicate refs rejected. |
| `test_cases.py` | Core 1 + 3 — case lifecycle (incl. invalid moves rejected, reopen from resolved/closed), assignment/reassignment, list filters. |
| `test_breach.py` | Core 4 — breach derived at read: past-due open = breached; future/no due = not; terminal status = never; same record reads differently at different `now` (derived, not stored). |
| `test_alerts.py` | Core 5 — alert ingest shape, opaque source refs, ack/resolve, link to case, bulk ingest atomicity (bad batch records nothing). |
| `test_schedules.py` | Core 6 — on-call derivation: anchor week, period rollover, rotation wrap, before-anchor backwards wrap, daily rotations; validation. |
| `test_rules.py` | Core 8 — rule registry records only: agent cannot write rules; a matching rule changes NO state (execution is Extended, pinned by test). |
| `test_status_reports.py` | Core 7 + 9 — status derivation (operational/degraded/outage), internal updates never leak into the public view, report counts, registry search. Core 9 is this group's one claimed function (VEN: agency "runs real-time reports"). |
| `test_service.py` | HTTP layer — health, 401 + denied-audit, role mismatch 401, viewer 403 + denied-audit, full flow incl. breach over HTTP, audit admin-only, rule write admin-only. |
| `test_main_cli.py` | CLI — no command exits 2, TLS cert/key pairing enforced, parser defaults. |
| `test_negative_control.py` | The load-bearing assertions for the mutation drill below. |

## Negative control — mutation record

**Drill performed** (Oct 25, 2026, against this group's own copy):
`CustsvcStore._is_breached` in `src/custsvc/store.py` was patched to
`return False` unconditionally (breach never derived). Result:
**7 failures** across 4 files — the same seven as Group 26's drill,
as expected of byte-identical code:

- `test_negative_control.py`: both tests (overdue case reads
  breached; breach counted in report and status view)
- `test_breach.py`: `test_past_due_open_case_is_breached`,
  `test_breach_is_derived_not_stored`
- `test_status_reports.py`: `test_breached_normal_case_is_degraded`,
  `test_report_counts`
- `test_service.py`: `test_full_flow` (breach asserted over HTTP)

Mutant output is saved at `scratch/mutation-test-output.txt`. The
file was then restored from `scratch/store.py.premutation` and
verified byte-identical (SHA-256
`05c749f34c37a977e76cb1372c035909ad09875a7180ff441ac876a489cffe06`,
recorded in `scratch/store.py.sha256`) — matching **both** the
recorded hash and Group 26's L1 original — and the suite returned
to **69/69 green** (re-run independently by the coordinator as well:
69 run, OK). An oracle that passes with breach derivation removed
would be testing that code ran, not that breach state is derived —
this control is the filter against that.

## Final GAPS batch — extension coverage (added 2026-11-07)

| File | Covers |
|---|---|
| `test_gaps_batch.py` | The extension surface in `src/custsvc/extensions.py` (`CustsvcExtensions` over the core store) — one class per open GAPS.md entry for this group (see `../BATCH.md` for dispositions): automation execution **request** records + verbatim outcome reports (the registry-never-executes doctrine pinned by behavior — a request changes no core state); GRC framework/control records + case→control mappings with posture counts derived at read; knowledge-base articles with append-only revisions (the stored article record holds no text); CSAT instruments + verbatim responses with tallies derived at read (mean as an exact rational, never a stored score); SLA policy records (terms as data) with breach state derived at read against the recorded terms; notification records with `reference_transport` delivery reports (nothing delivered) + status-page records over the core's derived public view (nothing hosted); analytics derivations beyond registry reporting (counts only). Stub labels on every reference record: commerce sites/reports, PCS relocation cases/steps (integer-cents data, floats/bools rejected, no id consumed), e-signature requests/reports (record shape holds no signature), detection sources + orchestration runs (a run creates no alert), channels/sessions (no media), assistants/deflection reports (case untouched). Cross-cutting: `ext_` actions and `:denied` denials on the core audit log; every stub-family record pinned to change no core record; an audit-write failure rolls the record and its id back. Plus negative control #2 (below). |

Suite status with the batch: **127 tests** (69 at delivery + 58 in
`test_gaps_batch.py`), all passing.

## Negative control #2 — SLA policy breach derivation (batch, 2026-11-07)

`test_gaps_batch.py::TestSlaNegativeControl` implements the mutant
for the extension surface's own derivation seam: a
`CustsvcExtensions` subclass (`MutantCustsvcExtensions`) whose
`_is_breached_under_policy` returns `False` unconditionally. The
traced claim is that **breach state under a recorded SLA policy is
derived** from the core case record (created_utc, priority,
status) against the policy's recorded per-priority targets — at
+61 minutes against a 60-minute high-priority target the case
reads breached; at +30 it does not. The test asserts the canonical
expectation from the real implementation, that the mutant would
NOT produce it, and that treating the mutant's outcome as
expected fails.

Mutation verification: VERIFIED by the coordinator (2026-11-07).
The seam's final return in `CustsvcExtensions._is_breached_under_policy`
(`src/custsvc/extensions.py`) was patched in the real file to
`return False`, the exact live counterpart of the in-suite mutant.
The full suite was run: **127 tests ran, exactly 3 failed** —

- `test_gaps_batch.TestSlaPolicies.test_breach_derived_from_recorded_terms`
- `test_gaps_batch.TestSlaPolicies.test_breach_report_counts`
- `test_gaps_batch.TestSlaNegativeControl.test_policy_breach_is_derived`

Mutant output is saved at `scratch/batch-mutation-output.txt`.
`extensions.py` was then restored from
`scratch/extensions.py.premutation` and verified byte-identical
(SHA-256
`adb6bdd3e6c0b5077ebc31761a07ad54b600f7e7b7148867c901639224f45a3f`,
recorded in `scratch/extensions.py.sha256`) and the suite re-run:
**127 tests, OK**. An oracle that passes with policy breach
derivation removed would be testing that code ran, not that
breach state is derived from recorded terms — this control is the
filter against that. (Negative control #1, the core `_is_breached`
drill, is unchanged above; its seam is in the byte-identical core
and was not touched.)
