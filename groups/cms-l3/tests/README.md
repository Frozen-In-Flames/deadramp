# Tests — Content Management System (CMS) L3-adjacent merged build

Stdlib `unittest` only. Every test docstring names the core function /
claim / control family it traces to.

This suite **extends the shipped Group 20 (CMS L2) suite**: the L2
tests were copied and pass with the minimal adaptations listed below,
and new files cover the High-baseline uplifts. Per the Merge Rule,
the merged fork inherits the higher tier (High) in full while
reusing Group 20's code (Apache-2.0, ours) wherever functions
overlap.

## Run

```bash
cd groups/cms-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 146 tests
```

Status at delivery: **146 tests, OK** against the implementation in
`../src/` (98 inherited from Group 20, 4 auditor tests added to the
inherited access file, 44 new uplift tests). Run exactly as above:
helpers are imported as a top-level module from the tests directory
and `tests/__init__.py` is empty by design.

## Layout

Inherited Group 20 files (covers as in Group 20's tests/README.md,
unchanged except the adaptations below): `test_access.py`,
`test_assets.py`, `test_audit.py`, `test_items_revisions.py`,
`test_lifecycle.py`, `test_publishing.py`, `test_report.py`,
`test_search.py`, `test_service.py`, `test_sites_sections.py`,
`test_tags_metadata.py`, `test_types.py`, `test_negative_control.py`,
`cms_helpers.py`.

| New / extended file | Tests | Covers |
|---|---:|---|
| `test_access.py` (extended) | +4 | **[L3] AC-5** auditor role: permission set exactly {audit_read}, can()/require() matrix, store-level denials for auditor reads/writes/search |
| `test_audit_chain.py` | 17 | **[L3] AU-9 / AU-3** hash chain: seq/prev_hash/hash fields, genesis, links, canonical-hash recomputation, `verify_chain()`, tamper localization (actor/action mutation, stripped hash, rewritten prev_hash, deleted entry), JSONL round-trip + file-edit detection after reload, `GET /audit/verify` (admin + auditor admitted, publisher 403, tamper reported); includes negative control #2 |
| `test_audit_query.py` | 14 | **[L3] AU-7** audit reduction: `AuditLog.query` filters (actor/action/target/since/until, combined, no-match) with pinned timestamps, `GET /audit` query params, auditor admitted / publisher denied |
| `test_audit_failure.py` | 6 | **[L3] AU-5** fail closed: `AuditWriteError` rollback in `record()`, chain still verifies after a failed record, store `_atomic` rollback (no site/item/revision, no id consumed), service `POST /sites` answers 500 and creates nothing |
| `test_lockout.py` | 6 | **[L3] AC-7** logon lockout over HTTP: below-threshold admission, threshold lock (correct role → 403), `auth:locked` audit, per-user scope (bob and dana unaffected), success resets counter, lock expiry (1 s lockout server) |
| `test_main_cli.py` (extended) | +1 | **[L3]** CLI: `--max-failed-logins` / `--lockout-seconds` flags accepted; dana (auditor) reads `/audit` and `/audit/verify`, denied `/sites` (403) |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON; genesis `prev_hash` = `"0"*64`); `verify_chain()` | AU-9, AU-3 | `audit.py` | `test_audit_chain.py` (13 unit/persistence tests) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_audit_chain.py` (4 endpoint tests) |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` query params | AU-7 | `audit.py`, `service.py` | `test_audit_query.py` (9 unit + 5 endpoint tests) |
| Fail closed on audit write failure: rollback + `AuditWriteError`; store `_atomic` snapshot rollback; service 500 | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_audit_failure.py` (6 tests) |
| Separation of duties: role `auditor` = {`audit_read`} only | AC-5 | `access.py`, `__main__.py` (demo user `dana=auditor`) | `test_access.py` (4 new tests), `test_main_cli.py`, endpoint tests |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server`; locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_lockout.py` (6 tests), `test_main_cli.py` |

All 12 L2 core functions keep their Group 20 coverage; the L3
public API contract is the L2 contract plus exactly the uplifts
above.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 20): a
   `CmsStore` subclass (`MutantCmsStore`) whose
   `_check_approver_not_author` is a no-op. For each canonical case
   (author-approve, author-return) the test asserts the canonical
   expectation (`PermissionDenied`, item stays `in_review`), that
   the mutant would NOT produce it, and — via a literal
   `assertRaises(AssertionError)` — that treating the mutant's
   outcome as expected fails. Cases use an editor-authored item
   reviewed by that same editor, so the author check is the only
   gate that can deny; a third test confirms a different reviewer
   succeeds on the real store.

   Mutation verification: VERIFIED by the coordinator for this group
   (2026-10-25). The guard in the real `CmsStore`
   (`src/cms/store.py`) was patched to a no-op (`return None`), the
   suite was run: **146 tests ran, 4 failed** —
   - `test_lifecycle.TestLifecycle.test_author_cannot_approve_own_item_store_level`
   - `test_lifecycle.TestLifecycle.test_editor_who_authored_cannot_review_own`
   - `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_approve_denied_canonical_but_mutant_approves`
   - `test_negative_control.TestNegativeControlMutantAuthorApproval.test_author_return_denied_canonical_but_mutant_returns`

   `store.py` was then restored from `tests/store.py.premutation`
   (SHA-256 `19b4f504275991fb8025e255f8c79da2adb456a8d02324d760b617aeb7bbd404`,
   verified identical before and after the drill) and the suite
   re-run: **146 tests, OK**.
2. **`test_audit_chain.py::TestTamperDetection`** [L3]: a clean log
   verifies `(True, None)`; mutating a stored entry in place
   (`log._entries[1]["actor"] = "mallory"`) must make
   `verify_chain()` report `(False, 1)` — proving the chain detects
   tampering rather than merely existing. Companion tests detect a
   mutated last entry, a stripped `hash` field, a rewritten
   `prev_hash`, a deleted middle entry, and an edited JSONL line
   after reload. Also verified externally by the coordinator at
   delivery: clean `(True, None)`, entry 1 mutated → `(False, 1)`.

## Group 20 test adaptations (complete list)

Every copied Group 20 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — one exact key-set assertion extended.**
   `test_record_roundtrip` asserted audit entries carry *exactly*
   `{ts, actor, action, target, details}`. Uplift 1 adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertion now
   requires exactly the original five keys plus the three chain
   keys. No other audit assertions changed.
2. **`test_access.py` — role set extended, auditor class added.**
   `test_roles_exact` now expects the six roles including
   `auditor`; `test_audit_read_admin_only`'s docstring records that
   the auditor role also holds `audit_read` [L3] (its assertions
   over the operational roles are unchanged — existing roles'
   permissions did not move). Four auditor tests were added in a new
   `TestAuditorRole` class (AC-5).
3. **`cms_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS`, mirroring the new demo user. No existing
   helper, user, or fixture changed; `test_service.py` (which
   consumes the registry) needed no edits — its auth-failure counts
   per username stay below the new default lockout threshold (max 1
   per user per class server), so no lockout trips.
4. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new AC-7
   flags and exercises the dana demo user; the original CLI test is
   byte-identical.
5. **`tests/store.py.premutation` — regenerated.** The pre-mutation
   copy now holds this group's uplifted `store.py` (SHA-256 above),
   since the drill restores the L3 store, not Group 20's.

No other Group 20 test file was modified (`test_assets.py`,
`test_items_revisions.py`, `test_lifecycle.py`,
`test_publishing.py`, `test_report.py`, `test_search.py`,
`test_service.py`, `test_sites_sections.py`,
`test_tags_metadata.py`, `test_types.py`,
`test_negative_control.py` are byte-identical to Group 20).

## Interpretation notes

Inherited from Group 20 and still in force:

- Publishing window state is derived at read time via
  `get_item(now=...)` / `list_items(now=...)`; the stored item
  status stays `published`.
- `GET /audit` returns `{"entries": [...]}`; asset bytes are never
  retained on any record.

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the query tests pin stored timestamps
  to fixed values so the windows are deterministic.
- `GET /audit/verify` reads the entry count *before* appending its
  own `audit_read` entry; the endpoint test asserts against the
  pre-request length.
- The AU-5 tests break the JSONL path mid-flight by replacing the
  file with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any
  platform.
- The inherited `test_service.py` 401 cases run against a shared
  class server; per-username failure counts there (alice 1, dave 1,
  mallory 1) stay below the AC-7 default threshold of 3, so the
  inherited expectations are unaffected by the lockout uplift.
