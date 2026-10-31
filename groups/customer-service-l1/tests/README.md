# Tests — custsvc (Group 26: Customer Service, L1)

Run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**80 tests, all passing** (Python stdlib `unittest` only, zero
third-party dependencies). Originally 69; the remainder addition
below added 11 (`test_additions.py`).

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
| `test_status_reports.py` | Core 7 + 9 — status derivation (operational/degraded/outage), internal updates never leak into the public view, report counts, registry search. |
| `test_service.py` | HTTP layer — health, 401 + denied-audit, role mismatch 401, viewer 403 + denied-audit, full flow incl. breach over HTTP, audit admin-only, rule write admin-only. |
| `test_main_cli.py` | CLI — no command exits 2, TLS cert/key pairing enforced, parser defaults. |
| `test_negative_control.py` | The load-bearing assertions for the mutation drill below. |
| `test_additions.py` | Remainder addition (Zendesk, FR1821856903) — spec integrity for a ZERO-CLAIM fork: sheet order/membership, the literal empty claim table, the originals' claim tables pinned as shipped, all-16 zero-claim set, census citations verified tagging nothing, near-miss pins, group totals (3 forks / 8 claims); plus 2 carried-substrate cases (help-desk flow with public status; breach derivation — trips under the drill). |

## Negative control — mutation record

**Drill performed** (Oct 25, 2026): `CustsvcStore._is_breached` in
`src/custsvc/store.py` was patched to `return False` unconditionally
(breach never derived). Result: **7 failures** across 4 files —

- `test_negative_control.py`: both tests (overdue case reads breached;
  breach counted in report and status view)
- `test_breach.py`: `test_past_due_open_case_is_breached`,
  `test_breach_is_derived_not_stored`
- `test_status_reports.py`: `test_breached_normal_case_is_degraded`,
  `test_report_counts`
- `test_service.py`: `test_full_flow` (breach asserted over HTTP)

The file was then restored from `scratch/store.py.premutation` and
verified byte-identical (SHA-256 `05c749f3…`, recorded in
`scratch/store.py.sha256`); the suite returned to **69/69 green**.
An oracle that passes with breach derivation removed would be testing
that code ran, not that breach state is derived — this control is the
filter against that.

**Drill re-run (remainder addition, Oct 31, 2026):** the core is
unchanged by the Zendesk addition, so the same drill was re-run in
this tree: `_is_breached` patched to `return False` unconditionally
(scoped replacement of the function body in `src/custsvc/store.py`,
pattern asserted to occur exactly once). Result: **80 tests ran,
exactly 8 failures** — the shipped drill's 7 (both
`test_negative_control.py` tests; `test_breach.py`:
`test_past_due_open_case_is_breached`,
`test_breach_is_derived_not_stored`; `test_status_reports.py`:
`test_breached_normal_case_is_degraded`, `test_report_counts`;
`test_service.py`: `test_full_flow`) plus 1 from the additions
module — `test_additions.py`:
`TestZendeskSubstrate.test_due_case_breach_derivation` — tripping
exactly as designed. Raw list in `scratch/additions_mutation_run.txt`.
The file was restored from `scratch/store.py.premutation-additions`
and verified byte-identical (SHA-256 `05c749f3…`); the suite returned
to **80/80 green**.
