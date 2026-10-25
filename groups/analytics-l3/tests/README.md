# Tests — Analytics L3 merged build (CMMC L3-adjacent / FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core function /
control family it traces to.

This suite **extends the shipped Group 1 (Analytics L2) suite**: the L2
tests were copied verbatim and pass unchanged except for the minimal
adaptations listed below, and new files cover the High-baseline
uplifts. Per the Merge Rule, the merged fork inherits the higher tier
(High) in full while reusing the Group 1 code (Apache-2.0, ours)
wherever functions overlap.

## Run

```bash
cd groups/analytics-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 183 tests
PYTHONPATH=src python3 -m unittest discover -s tests -t .   # package mode, also green
```

Status at delivery: **183 tests, OK** (136 inherited from Group 1,
47 added for the High uplifts).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 22 | 9 Access control — exact permission matrix, `require()`; **AC-5**: auditor role (8 new) |
| `test_audit.py` | 9 | 10 Audit log — entry keys, append-only, JSONL file + reopen |
| `test_audit_chain.py` | 14 | **AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, `verify_chain()`, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` |
| `test_audit_query.py` | 13 | **AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params |
| `test_audit_failure.py` | 5 | **AU-5** fail closed: `AuditWriteError` rollback in `record()`, store ingest creates no dataset, service ingest not a success |
| `test_lockout.py` | 6 | **AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, success resets counter, lock expiry |
| `test_store.py` | 18 | 1 Ingest, 2 Storage — registry, sequential `ds-N` ids, SI-10 atomic rejection |
| `test_query.py` | 36 | 3 Query & search — select, all 8 filter ops, grouping, ordering, limit, compound list forms |
| `test_describe.py` | 10 | 4 Descriptive statistics — exact mean/median/min/max/stddev, numeric-only rule |
| `test_charts.py` | 10 | 5 Visualization — bar/line/pie standalone SVG, no JS/external assets |
| `test_reports.py` | 9 | 6 Reporting, 7 Export — `report_html`, `result_to_csv`, `result_to_json` |
| `test_service.py` | 25 | 8 API access — live HTTP server: auth 401, permission 403, validation 400, missing 404, `{error}` envelope, denied attempts audited |
| `test_main_cli.py` | 2 | `python -m analytics serve` subprocess with demo users alice/bob/carol; **+1 new**: dana=auditor (AC-5) and `--max-failed-logins` / `--lockout-seconds` (AC-7) |
| `test_negative_control.py` | 4 | Negative control #1 (below), unchanged from Group 1 |
| `analytics_helpers.py` | — | Canonical sales dataset + row-shape normalisation; L3 adds the `AUDITOR` user / `dana` registry entry |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (3 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store/service propagate, operation does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (5 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only | AC-5 | `access.py`, `__main__.py` (demo user `dana=auditor`) | `test_access.py` (8 tests), `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 L2 core functions keep their Group 1 coverage unchanged (see
the file table); the L3 public API contract is the L2 contract plus
exactly the uplifts above.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 1): the mutant
   aggregation `avg` computed as `sum(values)`, ignoring the divisor.
   Each test asserts the canonical expectation (`statistics.mean`),
   that the implementation matches it, and — via a literal
   `assertRaises(AssertionError)` — that the canonical expectation
   rejects the mutant output, for the whole dataset, per group, and a
   second dataset.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field and a rewritten `prev_hash`, and an edited
   JSONL line after reload.

## Group 1 test adaptations (complete list)

Every copied Group 1 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — two exact key-set assertions relaxed to
   supersets.** `test_record_and_entries_roundtrip` and
   `test_file_backed_log_writes_jsonl` asserted audit entries carry
   *exactly* `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertions now
   require the original five keys (plus the three chain keys in the
   first test) as subsets. No other audit assertions changed — the
   original keys and values are unchanged, per the uplift spec.
2. **`test_access.py` — role-set test extended.**
   `test_roles_are_exactly_admin_analyst_viewer` became
   `test_roles_are_exactly_admin_analyst_viewer_auditor`: uplift 3
   adds the `auditor` role to `PERMISSIONS` / `ROLES`. All existing
   per-role permission assertions are unchanged (existing roles'
   permissions did not move). Eight auditor tests were added in a new
   `TestAuditorRole` class (AC-5).
3. **`analytics_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user. No
   existing helper, user, or dataset changed; `test_service.py`
   (which consumes the registry) needed no edits — its auth-failure
   counts per username stay below the new default lockout threshold
   (max 1 per user per class server), so no lockout trips.
4. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags and
   the dana demo user; the original CLI test is byte-identical.

No other Group 1 test file was modified (`test_store.py`,
`test_query.py`, `test_describe.py`, `test_charts.py`,
`test_reports.py`, `test_service.py`, `test_negative_control.py`
are byte-identical to Group 1).

## Interpretation notes

Inherited from Group 1 and still in force:

- `where`, `group_by`, `order_by` are **lists** (`query.py` docstring).
- `stddev` is the **population** standard deviation (describe docstring).
- CSV values are stored as strings; numeric behaviour comes from the
  query/describe layer's coercion — CSV-origin tests therefore compare
  through `float()`.
- `GET /datasets` returns `{"datasets": [...]}` and `GET /audit`
  returns `{"entries": [...]}`; bare lists are also accepted.

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps to
  fixed values so the windows are deterministic.
- `GET /audit/verify` reads the entry count *before* appending its own
  `audit_read` entry; the endpoint test asserts against the pre-request
  length.
- The AU-5 tests break the JSONL path mid-flight by replacing the file
  with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any platform.
