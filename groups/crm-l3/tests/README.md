# Tests — CRM L3-adjacent merged build (FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core
function / claim / control family it traces to.

This suite **extends the shipped Group 25 (CRM L2) suite**: the L2
tests were copied and pass with only the minimal adaptations listed
below, and new files cover the High-baseline uplifts. Per the Merge
Rule, the merged fork inherits the higher tier (High) in full while
reusing the Group 25 code (Apache-2.0, ours) wherever functions
overlap.

## Run

```bash
cd groups/crm-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 144 tests
```

Status at delivery: **144 tests, OK** (96 inherited from Group 25,
8 added inside inherited files for the uplifts, 40 in new files).

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 14 | Access control (RBAC) — exact permission matrix for admin/operator/viewer (14 actions), `permissions_for()`, `can()`, `require()`, unknown role/action denied; **[L3]** role set is exactly four, auditor role = `{audit_read}` only (AC-5, 6 tests) |
| `test_registry.py` | 12 | Account & contact registry — creation shape/provenance/defaults, opaque reference required + unique, unknown account → `NotFoundError`, list filter, copies-are-copies, viewer write denied, failed ops consume no ids |
| `test_privacy.py` | 4 | Privacy discipline — no entity shape carries a name/email/phone/ssn/dob/address/salary/score field; finding detail stored verbatim; the report contains no score/average aggregate |
| `test_cases.py` | 22 | Cases — creation/validation, assignment, full lifecycle + reopen + cancel, invalid transitions, breach derivation (derived-not-stored), list filters, no-id-on-failure |
| `test_interactions.py` | 7 | Interactions — recording, all channels/directions, validation + linked-id checks, immutability, filters |
| `test_guides.py` | 8 | Guides — creation at version 1, all kinds, validation, versioned updates, copies-are-copies, viewer write denied |
| `test_findings.py` | 6 | Findings — creation with verbatim detail, severities, lifecycle, invalid transitions, filters |
| `test_modules.py` | 6 | Modules — creation at version 1, validation, **admin-only write**, versioned updates, viewer read allowed |
| `test_reports_search.py` | 7 | Reports + search — report shape/counts incl. derived breach at `now`, empty store; search shape, matching, literal-not-regex, empty query → `ValidationError`, search audited |
| `test_audit.py` | 6 | Append-only audit log — entry keys (superset incl. [L3] chain fields), User actor normalised, append-only/copies, JSONL persistence + reload (in group `scratch/`), store recording every mutation action, failed ops record nothing |
| `test_audit_chain.py` | 15 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash, links, `verify_chain()`, JSONL round-trip + file-edit detection, negative control #2, `GET /audit/verify` (incl. auditor allowed, viewer/operator denied) |
| `test_audit_query.py` | 13 | **[L3] AU-7** audit reduction & search: `AuditLog.query` filters (actor/action/target/since/until), `GET /audit` query params, auditor can use the reduced search |
| `test_audit_failure.py` | 6 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, store create/transition roll back in full (no record, no id consumed), service create is not a success |
| `test_lockout.py` | 6 | **[L3] AC-7** unsuccessful logon lockout over HTTP: threshold, `auth:locked` audit, per-user scope, success resets counter, lock expiry |
| `test_service.py` | 8 | REST API — live HTTP server: health, 401s, 403s audited `:denied`, full flow, `audit_read` admin + **[L3]** auditor allowed / registry denied for auditor, 400/404 envelopes, `?now=` derivation |
| `test_main_cli.py` | 3 | `python -m crm serve` subprocess with demo users alice/bob/carol; **[L3] +1**: dana=auditor and `--max-failed-logins` / `--lockout-seconds` |
| `test_negative_control.py` | 1 | Negative control #1 (below), unchanged from Group 25 |
| `crm_helpers.py` | — | Shared fixtures: demo users (ADMIN/OPERATOR/VIEWER + **[L3]** AUDITOR), `USERS` registry (incl. dana), `fresh_store()`, `make_store()` |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (11 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (8 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store rolls the whole operation back (snapshot), service does not proceed | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (6 tests) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `service.py`, `__main__.py` | `test_access.py` (6 tests), `test_service.py`, `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 10 L2 core functions keep their Group 25 coverage unchanged
(see the file table); the L3 public API contract is the L2 contract
plus exactly the uplifts above.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 25): a
   `CrmStore` subclass (`MutantCrmStore`) overriding the derivation
   point — `_is_breached` always returns `False`. The test asserts
   the canonical expectation (an overdue open case reads
   `breached=True`, and a report at that `now` counts it), that the
   mutant would NOT produce it, and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails.
2. **`test_audit_chain.py::test_negative_control_2_mutated_entry_fails_at_index_1`**:
   a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   stripped `hash` field, a rewritten `prev_hash`, and an edited
   JSONL line after reload.

## Mutation verification

Both drills were performed live by the builder (2026-10-25) on the
real implementation (not just the subclass mutants):

**Drill 1 — breach derivation (inherited control).** The body of
`CrmStore._is_breached` (`src/crm/store.py`) was patched to
`return False`, the exact live counterpart of the mutant in
`test_negative_control.py`. The full suite was run: **144 tests ran,
7 failed** —

- `test_cases.TestBreachDerivation.test_in_progress_past_due_breached`
- `test_cases.TestBreachDerivation.test_now_forms`
- `test_cases.TestBreachDerivation.test_overdue_open_case_breached`
- `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_case_breached_canonical_but_mutant_not`
- `test_reports_search.TestReport.test_report_breach_is_now_dependent`
- `test_reports_search.TestReport.test_report_shape_and_counts`
- `test_service.TestService.test_full_flow`

(the identical failure set to Group 25's drill). `store.py` was
then restored from a pre-mutation copy
(`scratch/store.py.premutation`; SHA-256
`bd9516e567ca857612498ece15f65a8464f5bd04d96a0496fb3381879cd7804a`,
recorded in `scratch/store.py.sha256` and verified identical after
restore) and the suite re-run: **144 tests, OK**.

**Drill 2 — audit verifier [L3].** `AuditLog.verify_chain`
(`src/crm/audit.py`) was patched to return `(True, None)`
unconditionally — a verifier that never verifies. The audit test
files were run: **40 tests ran, 4 failed** —

- `test_audit_chain.TestVerifyChain.test_negative_control_2_mutated_entry_fails_at_index_1`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_broken_link`
- `test_audit_chain.TestVerifyChain.test_verify_chain_detects_missing_hash_fields`
- `test_audit_chain.TestHashChainPersistence.test_edited_jsonl_line_fails_verification_after_reload`

`audit.py` was then restored from `scratch/audit.py.premutation`
(SHA-256
`18cbe909214ffe6f4268d2b83e93967673d3b8402be684c5a12802c38c357c99`,
recorded in `scratch/audit.py.sha256` and verified identical after
restore) and the full suite re-run: **144 tests, OK**. The suite
catches both defect classes; neither negative control is decorative.

## Group 25 test adaptations (complete list)

Every copied Group 25 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — one exact key-set assertion relaxed to a
   superset.** `test_entry_keys` asserted audit entries carry
   *exactly* `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertion now
   requires the original five keys plus the three chain keys as
   subsets. No other audit assertion changed.
2. **`test_access.py` — additive only.** One role-set test plus a
   new `TestAuditorRole` class (6 tests, AC-5). All existing
   per-role permission assertions are unchanged (existing roles'
   permissions did not move).
3. **`crm_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS`, mirroring the new demo user. No existing
   helper, user, or fixture changed; `test_service.py` (which
   consumes the registry) needed one additive test only — its
   auth-failure counts per username stay below the new default
   lockout threshold (max 1 per user), so no lockout trips.
4. **`test_service.py` — additive only.** One new test
   (`test_audit_read_auditor_allowed_registry_denied`); the original
   `test_audit_read_admin_only` docstring now reads "among L2 roles"
   (its assertions are unchanged).
5. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags and
   the dana demo user; the original CLI tests are byte-identical.

No other Group 25 test file was modified (`test_registry.py`,
`test_privacy.py`, `test_cases.py`, `test_interactions.py`,
`test_guides.py`, `test_findings.py`, `test_modules.py`,
`test_reports_search.py`, `test_negative_control.py` are
byte-identical to Group 25).

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
