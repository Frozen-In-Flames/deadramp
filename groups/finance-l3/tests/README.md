# Tests — Finance L3-adjacent singleton build (FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core
function / spec claim / control family it traces to.

This suite **extends the shipped Group 31 (Finance L2) suite**:
the L2 tests were copied and pass with only the minimal
adaptations listed below, and new files cover the High-baseline
uplifts. Per the Merge Rule, the merged fork inherits the higher
tier (High) in full while reusing the Group 31 code (Apache-2.0,
ours) wherever functions overlap.

## Run

```bash
cd groups/finance-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 249 tests
```

Status at delivery: **249 tests, OK** (202 inherited from Group
31, 7 added inside inherited files for the uplifts, 40 in new
files).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 23 | Access control (RBAC) — exact permission matrix for admin/member/viewer (8 actions), `permissions_for()`, `can()`, `require()`, unknown role/action denied; **[L3]** role set is exactly four, auditor role = `{audit_read}` only (AC-5, 5 new tests) |
| `test_audit.py` | 13 | Append-only audit log — entry keys (superset incl. [L3] chain fields), User actor normalised, append-only/copies, JSONL persistence + reload (in group `scratch/`), store recording every mutation action, failed ops record nothing |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, `verify_chain()`, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` (incl. auditor allowed, member/viewer denied) |
| `test_audit_query.py` | 13 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params, auditor can use the reduced search |
| `test_audit_failure.py` | 6 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, store create/status-change roll back in full (no record, no id consumed), service create is not a success |
| `test_bookings.py` | 24 | Travel booking records — creation/validation, lifecycle confirm/cancel, filters, no-id-on-failure |
| `test_budgets.py` | 19 | Spend budgets & tracking — set/replace, spend-vs-budget computation from records, unbudgeted categories, variance/over-budget |
| `test_earned_wage.py` | 49 | Earned-wage accrual & access — accrual views (derived accessed/pending/available), the earned-cap invariant, approval machine with separation of duties, disbursement records |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, success resets counter, lock expiry |
| `test_main_cli.py` | 2 | `python -m finance serve` subprocess with demo users alice/bob/carol; **[L3] +1**: dana=auditor and `--max-failed-logins` / `--lockout-seconds` |
| `test_negative_control.py` | 3 | Negative control #1 (below), unchanged from Group 31 |
| `test_programs.py` | 36 | Programs & members, participant registry — creation shapes/provenance, membership boundary, opaque-ref privacy pin, status changes |
| `test_reports.py` | 7 | Reporting — program summary computed on read from records only |
| `test_service.py` | 17 | REST API — live HTTP server: health, 401s, 403s audited `:denied`, full flow, `audit_read` admin among L2 roles + **[L3]** auditor allowed / programs denied for auditor, 400/404 envelopes, over-cap over HTTP |
| `test_wellness.py` | 16 | Financial wellness offering registry — offerings, enrollments, duplicate enrollment rejected |
| `finance_helpers.py` | — | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER + **[L3]** AUDITOR), `USERS_REGISTRY` (incl. dana), `fresh_store()`, `make_store()`, accrual/participant builders |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (snapshot), service does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (6 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py` (5 tests), `test_service.py`, `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 11 L2 core functions keep their Group 31 coverage unchanged
(see the file table); the L3 public API contract is the L2 contract
plus exactly the uplifts above. The earned-cap invariant and the
integer-cents boundary carry unchanged and keep their Group 31
tests (`test_earned_wage.py`, byte-identical).

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 31): the
   mutant cap check — a `_check_access_cap` replacement that sums
   the committed and requested amounts but never compares the
   total against the period's earned amount, treating every
   request as within cap. Each test asserts (1) the canonical
   expectation — the real store raises `ValidationError` for a
   request that would push a period's committed total even one
   cent over its earned amount, stores nothing, and consumes no
   id; (2) the mutant would NOT raise; and (3) — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain
   detects tampering rather than merely existing. Companion tests
   detect a stripped `hash` field, a rewritten `prev_hash`, and an
   edited JSONL line after reload.

## Mutation verification

Both drills were performed live by the coordinator (2026-10-31) on
the real implementation (not just the subclass/in-test mutants):

**Drill 1 — earned cap (inherited control).** The comparison in
`_check_access_cap` (`src/finance/store.py`) was patched out — the
body sums the committed and requested amounts and returns `True`
unconditionally, the exact live counterpart of the mutant in
`test_negative_control.py`. The full suite was run: **249 tests
ran, 5 failed** —

- `test_earned_wage.TestRequestFlow.test_request_one_cent_over_cap_is_rejected_whole`
- `test_earned_wage.TestRequestFlow.test_two_requests_summing_over_cap_second_is_rejected`
- `test_negative_control.TestNegativeControlMutantCapCheck.test_single_request_one_cent_over_earned`
- `test_negative_control.TestNegativeControlMutantCapCheck.test_two_requests_each_within_earned_whose_sum_exceeds_it`
- `test_service.TestServiceValidation.test_over_cap_request_over_http_is_400_and_creates_nothing`

`store.py` was then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`6ec44f3c1568e5e53c55261e0c9c689b6e2cf2defac65d7e87f41ece658b236f`,
recorded in `scratch/store.py.sha256` and verified identical
after restore) and the suite re-run: **249 tests, OK**.

**Drill 2 — audit verifier [L3].** `AuditLog.verify_chain`
(`src/finance/audit.py`) was patched to return `(True, None)`
unconditionally — a verifier that never verifies. The audit test
files were run: **47 tests ran, 4 failed** —

- `test_audit_chain.TestVerifyChain.test_negative_control_2_mutated_entry_fails_at_index_1`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_broken_link`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_missing_hash_fields`
- `test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_fails_verification_after_reload`

(the identical failure set to Group 40's drill 2). `audit.py` was
then restored from `scratch/audit.py.premutation` (SHA-256
`c027a74b04d63f05f6b7dd374ea9450fff445a63d7233a73221d73a29b6c7c55`,
recorded in `scratch/audit.py.sha256` and verified identical after
restore) and the full suite re-run: **249 tests, OK**. The suite
catches both defect classes; neither negative control is
decorative.

## Group 31 test adaptations (complete list)

Every copied Group 31 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — two exact key-set assertions relaxed to
   supersets.** The record-roundtrip and JSONL-file tests asserted
   audit entries carry *exactly* `{ts, actor, action, target,
   details}`. Uplift 1 adds `seq` / `prev_hash` / `hash` to every
   entry, so the assertions now require the original five keys
   plus the three chain keys as subsets. No other audit assertions
   changed.
2. **`test_access.py` — role-set test extended, additive class.**
   `test_roles_are_exactly_admin_member_viewer` became
   `test_roles_are_exactly_admin_member_viewer_auditor`; a new
   `TestAuditorRole` class (5 tests, AC-5) was added. All existing
   per-role permission assertions are unchanged (existing roles'
   permissions did not move).
3. **`finance_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user. No
   existing helper, user, or fixture changed. Lockout safety was
   verified before the port: the inherited `test_service.py` makes
   at most 1 auth failure per username per class server, so no
   inherited test trips the new default lockout threshold.
4. **`test_service.py` — additive only.** One new test
   (`test_audit_read_auditor_allowed_programs_denied`); the
   original `test_audit_endpoint_is_admin_only` docstring now
   opens "Among L2 roles" (its assertions are unchanged).
5. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags
   and the dana demo user; the original CLI test is unchanged.

No other Group 31 test file was modified (`test_bookings.py`,
`test_budgets.py`, `test_earned_wage.py`,
`test_negative_control.py`, `test_programs.py`,
`test_reports.py`, `test_wellness.py`, `__init__.py` are
byte-identical to Group 31, SHA-256 verified).

Port notes (CRM L3 test files → finance): the finance service
exports no `USERS` constant, so the uplift endpoint/lockout/
failure tests use `dict(USERS_REGISTRY)` from `finance_helpers`;
CRM's `operator` role is finance's `member`; CRM's `/accounts`
fixtures are finance program creations (`create_program(name,
actor)`); `test_audit_query.py`'s pinned fourth synthetic entry is
a `budget_set` action (finance has no CRM `search` action).

## Interpretation notes

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts`
  string, inclusive on both ends — the query tests pin stored
  timestamps to fixed values so the windows are deterministic.
- `GET /audit/verify` reads the entry count *before* appending its
  own `audit_read` entry; the endpoint test asserts against the
  pre-request length.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform.
- The AC-7 expiry test uses a separate server with
  `lockout_seconds=1` and a real 1.2-second sleep (the proven
  CRM L3 approach); no clock is monkeypatched.
