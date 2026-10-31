# Tests — custsvc (Group 41 singleton: Customer Service, L3-adjacent)

Run from the group directory:

```
PYTHONPATH=src python3 -m unittest discover -s tests
```

**126 tests, all passing** (Python stdlib `unittest` only, zero
third-party dependencies; 112 shipped + 14 remainder-addition
tests — see the additions record at the end of this file).

This suite **extends the shipped Group 26/27 (Customer Service
L1/L2) suite**: the inherited tests were copied and pass with only
the minimal adaptations listed below, and new files cover the
High-baseline uplifts. Per the Merge Rule, the merged fork inherits
the higher tier (High) in full while reusing the Group 26/27 code
(Apache-2.0, ours) wherever functions overlap.

Status at delivery: **112 tests, OK** (69 inherited from Groups
26/27, 7 added inside inherited files for the uplifts, 36 in new
files). The suite takes ~14s: most fixtures run a live HTTP server.
The remainder addition (below) brings the suite to **126 tests,
OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 11 | Core 10 — RBAC matrix: admin ⊇ all; agent writes cases/requesters/responders/alerts/schedules but NOT rules or audit; viewer read-only, no audit; unknown roles denied. **[L3]** +6: auditor role = `{audit_read}` only (AC-5), existing roles unchanged, role set exactly four |
| `test_audit.py` | 4 | Core 10 — append-only audit: entry shape/order (key set now includes the [L3] chain fields), no update/delete API, store mutations recorded with actor names |
| `test_requesters.py` | 6 | Core 2 — requester privacy is structural: exact record key set pinned, no contact fields exist, duplicate refs rejected |
| `test_cases.py` | 8 | Core 1 + 3 — case lifecycle (incl. invalid moves rejected, reopen from resolved/closed), assignment/reassignment, list filters |
| `test_breach.py` | 6 | Core 4 — breach derived at read: past-due open = breached; future/no due = not; terminal status = never; same record reads differently at different `now` (derived, not stored) |
| `test_alerts.py` | 8 | Core 5 — alert ingest shape, opaque source refs, ack/resolve, link to case, bulk ingest atomicity (bad batch records nothing) |
| `test_schedules.py` | 7 | Core 6 — on-call derivation: anchor week, period rollover, rotation wrap, before-anchor backwards wrap, daily rotations; validation |
| `test_rules.py` | 4 | Core 8 — rule registry records only: agent cannot write rules; a matching rule changes NO state (execution is Extended, pinned by test) |
| `test_status_reports.py` | 8 | Core 7 + 9 — status derivation (operational/degraded/outage), internal updates never leak into the public view, report counts, registry search |
| `test_service.py` | 8 | HTTP layer — health, 401 + denied-audit, role mismatch 401, viewer 403 + denied-audit, full flow incl. breach over HTTP, audit admin-only, rule write admin-only |
| `test_main_cli.py` | 4 | CLI — no command exits 2, TLS cert/key pairing enforced, parser defaults. **[L3]** +1: `--max-failed-logins` / `--lockout-seconds` defaults (AC-7) |
| `test_negative_control.py` | 2 | Negative control #1 (below), unchanged from Groups 26/27 |
| `test_audit_chain.py` | 13 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, `verify_chain()`, deleted-entry detection, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` (admin + auditor allowed, agent/viewer 403) |
| `test_audit_failure.py` | 5 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, store create/status roll back in full (no record, no id consumed), service create is not a success |
| `test_audit_query.py` | 12 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params, auditor can use the reduced search, agent cannot |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, below-threshold admission, success resets counter, lock expiry |
| `test_additions.py` | 14 | **Remainder addition** (unit `addition:customer-service-l3`): spec integrity for the Medallia sheet (membership, literal 2-claim table, verbatim description/evidence, census citations, no-exclusion pin, absence accounting, near-miss pins) + 2 substrate cases (feedback-case breach flow; audit-chain tamper localization) |
| `custsvc_helpers.py` | — | Shared fixtures: demo users (ADMIN/AGENT/VIEWER + **[L3]** AUDITOR), `make_store()`, `make_case()` |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (9 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (6 unit + 6 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (snapshot: records + id counters); service does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (5 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py` (6 tests), endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 core functions keep their Group 26/27 coverage unchanged
(see the file table); the L3 public API contract is the L1/L2
contract plus exactly the uplifts above.

## Group 26/27 test adaptations (complete list)

10 of the 14 inherited files are byte-identical to the Group 27
copies (`__init__.py`, `test_alerts.py`, `test_breach.py`,
`test_cases.py`, `test_negative_control.py`, `test_requesters.py`,
`test_rules.py`, `test_schedules.py`, `test_service.py`,
`test_status_reports.py`). The four deliberate, uplift-driven
changes:

1. **`custsvc_helpers.py` — additive only.** Added
   `AUDITOR = User(name="dana", role="auditor")` [L3], mirroring the
   new demo user. No existing helper, user, or fixture changed;
   `test_service.py` (which consumes the service `USERS` registry,
   now including dana) needed no edits — its per-user auth-failure
   counts stay at one per test (fresh server per test), far below
   the new default lockout threshold.
2. **`test_audit.py` — one exact key-set assertion extended.**
   `test_entries_shape_and_order` asserted audit entries carry
   exactly `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertion now
   names all eight keys. No other audit assertion changed — the
   original keys and values are unchanged.
3. **`test_access.py` — additive only.** One new test class
   (`TestAuditorRole`, 6 tests, AC-5) and the `AUDITOR` import; the
   original matrix tests are unchanged (existing roles' permissions
   did not move).
4. **`test_main_cli.py` — additive only.** One new test
   (`test_lockout_flag_defaults`) asserting the AC-7 flag defaults;
   the original three CLI tests are unchanged.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Groups 26/27):
   the load-bearing breach assertions. **Drill performed** (Oct 31,
   2026, against this group's own copy): `CustsvcStore._is_breached`
   in `src/custsvc/store.py` was patched to `return False`
   unconditionally (breach never derived). Result: **exactly 7
   failures** — the same seven as the Group 26 and Group 27 drills,
   as expected of the carried code:

   - `test_negative_control.py`: both tests (overdue case reads
     breached; breach counted in report and status view)
   - `test_breach.py`: `test_past_due_open_case_is_breached`,
     `test_breach_is_derived_not_stored`
   - `test_status_reports.py`: `test_breached_normal_case_is_degraded`,
     `test_report_counts`
   - `test_service.py`: `test_full_flow` (breach asserted over HTTP)

   Mutant output is saved at `scratch/mutation-test-output.txt`.
   The file was then restored from `scratch/store.py.premutation`
   and verified byte-identical (SHA-256
   `40c4d9c6ad5f4b3f12c4876cd9de5ccdfe829bfc5578343b9585a4bd7cc2b24a`,
   recorded in `scratch/store.py.sha256`) — the uplifted store, not
   the L2 original — and the suite returned to **112/112 green**.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field, a rewritten `prev_hash`, a deleted middle
   entry, and an edited JSONL line after reload. **Drill performed**
   (Oct 31, 2026): the hash comparison in `verify_chain()` was
   patched out (`if expected != stored_hash:` → `if False:`).
   Result: **exactly 2 failures** across the full suite — precisely
   the two tests that depend on hash comparison
   (`test_negative_control_2_mutated_entry_fails_at_index_1` and
   `test_edited_jsonl_line_detected_after_reload`); the seq /
   prev-hash linkage tests kept passing, as they test a different
   mechanism. Mutant output at `scratch/mutation-audit-output.txt`;
   `audit.py` restored from `scratch/audit.py.premutation`,
   SHA-256-verified (`3d0965771e6a38c3ddc3da82686a2afa55de6b5f20101d961e5d10ee308f8157`),
   suite green again.

## Remainder addition — drill re-runs (Oct 31, 2026)

The remainder addition (Medallia GovCloud, `../ADDENDUM.md`) adds
`test_additions.py` (14 tests) and changes no core code, so **both**
signature drills were re-run in this tree against the enlarged
suite (126 tests):

1. **Breach drill.** `CustsvcStore._is_breached`'s final return in
   `src/custsvc/store.py` was patched to `return False` (the target
   line occurs exactly once; count asserted, patch scoped — the
   net effect is breach never derived, the shipped drill's
   mutant). Result: **exactly 8 failures** — the shipped drill's
   7 (`test_breach.py` ×2, `test_negative_control.py` ×2,
   `test_status_reports.py` ×2, `test_service.py` ×1) plus exactly
   1 from the additions module
   (`test_additions.py::test_medallia_feedback_case_breach_flow`),
   tripping as designed. Mutant output at
   `scratch/additions_mutation_run.txt`; `store.py` restored from
   `scratch/additions_store.py.premutation`, SHA-256-verified
   identical to the shipped hash
   (`40c4d9c6ad5f4b3f12c4876cd9de5ccdfe829bfc5578343b9585a4bd7cc2b24a`),
   suite green.
2. **Audit-hash drill.** The hash comparison in `verify_chain()`
   (`src/custsvc/audit.py`, `if expected != stored_hash:` → `if
   False:`; the line occurs exactly once, count asserted). Result:
   **exactly 3 failures** — the shipped drill's 2
   (`test_negative_control_2_mutated_entry_fails_at_index_1`,
   `test_edited_jsonl_line_detected_after_reload`) plus exactly 1
   from the additions module
   (`test_additions.py::test_medallia_audit_chain_detects_tampering`),
   tripping as designed. Mutant output at
   `scratch/additions_mutation_audit_run.txt`; `audit.py` restored
   from `scratch/additions_audit.py.premutation`, SHA-256-verified
   identical to the shipped hash
   (`3d0965771e6a38c3ddc3da82686a2afa55de6b5f20101d961e5d10ee308f8157`),
   suite green. Final state: **126 tests, OK**, and the full
   `src/` tree is byte-identical to the shipped build.
