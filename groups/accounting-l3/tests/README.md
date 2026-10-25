# Tests — Accounting L3 merged build (CMMC L3-adjacent / FedRAMP High)

Stdlib `unittest` only. Every test docstring names the core function /
control family it traces to.

This suite **extends the shipped Group 5 (Accounting L2) suite**: the L2
tests were copied verbatim and pass unchanged except for the minimal
adaptations listed below, and a new file covers the High-baseline
uplifts. Per the Merge Rule, the merged fork inherits the higher tier
(High) in full while reusing the Group 5 code (Apache-2.0, ours)
wherever functions overlap.

## Run

```bash
cd groups/accounting-l3
PYTHONPATH=src python3 -m unittest discover -s tests        # 273 tests
```

Status at delivery: **273 tests, OK** (219 inherited from Group 5,
54 added for the High uplifts: 53 in `test_l3_uplifts.py` plus 1 in
`test_main_cli.py`). (Run exactly as above: helpers are imported as a
top-level module from the tests directory and `tests/__init__.py` is
empty by design, so package-mode discovery with `-t .` is not the
supported entry point for this group.)

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 18 | 12 Access control — exact permission matrix for admin/member/viewer (admin all ten actions; member {read, create_book, enter, submit, approve, pay, close}; viewer {read}), `permissions_for()`, `can()`, `require()`, unknown role/action/user denied; role-set test extended for **auditor** (see adaptations) |
| `test_audit.py` | 13 | 13 Audit log — entry keys, append-only, JSONL file + reload on construction, and the store recording each mutation action (`book_create`, `member_add`, `account_create`, `entry_create`, `entry_submit`, `entry_post`, `entry_reject`, `entry_void`, `invoice_create`, `invoice_submit`, `invoice_issue`, `invoice_reject`, `invoice_void`, `payment_record`, `expense_create`, `expense_submit`, `expense_approve`, `expense_reject`, `expense_void`, `expense_reimburse`, `budget_set`, `reconciliation_create`, `period_close`); two key-set assertions adapted for the chain fields (see adaptations) |
| `test_books.py` | 30 | 1 Books & members + 2 Chart of accounts — book creation shape/provenance, `book-` id sequence, list visibility, owner-or-admin `add_member`, membership boundary, failed ops consume no ids; accounts: creation shape, duplicate code rules, cross-book `NotFoundError` |
| `test_budgets.py` | 21 | 7 Budgets — `set_budget` shape + total, replace semantics, duplicate/unknown account lines, budget-vs-actual math |
| `test_expenses.py` | 17 | 6 Expenses + 10 Workflow & approvals — creation shape/validation, machine to approved/reimbursed, SoD on approve |
| `test_invoices.py` | 29 | 4 Invoicing & billing + 5 Payments + 10 Workflow & approvals — computed totals in integer cents, machine to issued/paid, overpayment rejected whole, `list_payments` filter |
| `test_ledger.py` | 34 | 3 Double-entry journal & ledger posting + 10 Workflow & approvals — balanced entry creation, unbalanced entries rejected with nothing stored and no id consumed, SoD approve/reject, void rules |
| `test_reports.py` | 22 | 9 Financial reporting — canonical scenario (invest 100000¢, earn 50000¢, rent 20000¢): trial balance, `account_balance`, `account_activity`, income statement, balance sheet |
| `test_reconciliation.py` | 14 | 8 Reconciliation & period close — matched/difference reconciliation, close semantics, closed-period entry/approve rejection |
| `test_service.py` | 17 | 11 API access — live HTTP server: `/health` without auth, 401 unknown user and role mismatch, 403 permission denials, full flow book → paid invoice, SoD over HTTP, unbalanced entry → 400 with nothing created, audit endpoint admin-only, denied attempts recorded with `:denied` suffix |
| `test_main_cli.py` | 2 | `python -m accounting serve` subprocess with demo users alice/bob/carol; **+1 new**: dana=auditor (AC-5) and `--max-failed-logins` / `--lockout-seconds` (AC-7) |
| `test_negative_control.py` | 3 | Negative control #1 (below), unchanged from Group 5 |
| `test_l3_uplifts.py` | 53 | **All six L3 uplifts** — hash chain fields/genesis/independent recomputation/links, `verify_chain()` clean + tamper at exact index (in-memory and after JSONL reload), negative control #2, fail-closed `record()` / store rollback (book, account, entry-submit, payment) / service, `AuditLog.query` filters + `GET /audit` params, `GET /audit/verify`, AC-7 lockout (threshold, `auth:locked`, per-user, success resets, expiry), AC-5 auditor role (unit + endpoints) |
| `accounting_helpers.py` | — | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `make_store()`, `make_chart()`, `post_entry()` and the canonical posted-scenario builders; L3 adds the `AUDITOR` user / `dana` registry entry (see adaptations) |

## Coverage map — High-baseline uplifts

| Uplift | Control family | Implementation | Tests |
|---|---|---|---|
| Tamper-evident hash chain on every audit entry (`seq`, `prev_hash`, `hash` = SHA-256 of canonical JSON of {seq, ts, actor, action, target, details, prev_hash}; genesis `prev_hash` = `"0"*64`); `verify_chain()` → `(ok, first_bad_index_or_None)` | AU-9, AU-3 | `audit.py` | `test_l3_uplifts.py` — `TestHashChainFields` (4), `TestVerifyChain` (5), `TestHashChainPersistence` (2) |
| `GET /audit/verify` → `{ok, entries, first_bad_index}` (audit_read) | AU-9, AU-6 | `service.py` | `test_l3_uplifts.py` — `TestAuditVerifyEndpoint` (3), `TestAuditorEndpoints` |
| Audit reduction & search: `AuditLog.query(actor, action, target, since, until)`; `GET /audit` filter params (actor, action, target, since, until) | AU-7 | `audit.py`, `service.py` | `test_l3_uplifts.py` — `TestAuditQuery` (8), `TestAuditQueryEndpoint` (6) |
| Fail closed on audit write failure: `record()` rollback + `AuditWriteError` (new in `errors.py`); the store rolls back the whole mutation via a snapshot/restore wrapper on every mutating method — no object created, no id consumed, state exactly as before; the service propagates | AU-5 | `audit.py`, `errors.py`, `store.py`, `service.py` | `test_l3_uplifts.py` — `TestRecordFailClosed` (4), `TestStoreFailClosed` (4), `TestServiceFailClosed` (1) |
| Separation of duties: role `auditor` = `{audit_read}` only; demo user `dana=auditor` | AC-5 | `access.py`, `__main__.py` | `test_l3_uplifts.py` — `TestAuditorRole` (6), `TestAuditorEndpoints` (4); `test_main_cli.py` (1) |
| Unsuccessful logon lockout: `max_failures` / `lockout_seconds` on `make_server` (defaults 3 / 300); locked attempts → 403 + `auth:locked` audit; success resets; expiry re-admits | AC-7 | `service.py`, `__main__.py` (`--max-failed-logins`, `--lockout-seconds`) | `test_l3_uplifts.py` — `TestLockout` (5), `TestLockoutExpiry` (1); `test_main_cli.py` (1) |

All Group 5 core behavior keeps its inherited coverage unchanged (see
the file table): integer cents only (floats/bools rejected at the
boundary), approval-gated posting with separation of duties, and every
endpoint and semantic from the L2 contract. The L3 public API contract
is the L2 contract plus exactly the uplifts above.

## Negative controls

1. **`test_negative_control.py`** (unchanged from Group 5): the mutant
   balance check that computes the debit and credit sums but **never
   compares them**, treating every entry as balanced. For each
   canonical case — (a) an unbalanced entry (debits 10000, credits
   9999) and (b) individually valid lines whose total debits exceed
   credits by 1 cent — the test asserts the canonical expectation
   (`ValidationError` from the real store, nothing stored, no entry id
   consumed), that the mutant gate would NOT raise, and — via a
   literal `assertRaises(AssertionError)` — that treating the mutant's
   outcome as the expected outcome fails. Case (c) is the control
   sanity check: a genuinely balanced entry passes both.

   **Mutation drill (performed for real in this build, 2026-10-25):**
   the real balance check in `AccountingStore.create_entry`
   (`src/accounting/store.py`) was patched from
   `if total_debits != total_credits or total_debits <= 0:` to
   `if total_debits <= 0:` — the exact live counterpart of the mutant,
   computing the sums but never comparing them — and the full suite
   was run: **273 tests ran, 4 failed**. The failures are exactly the
   defect class's surface, the same four as the Group 5 drill:
   `test_ledger`'s `test_unbalanced_entry_is_rejected_and_stores_nothing`,
   both negative-control unbalanced cases (10000 vs 9999, and debits
   exceeding credits by one cent), and `test_service`'s
   `test_unbalanced_entry_over_http_is_400_and_creates_nothing`.
   `store.py` was then restored from the pre-mutation copy kept at
   `../scratch/store.py.premutation` (SHA-256 verified identical to
   the pre-mutation hash recorded in `../scratch/store.py.sha256`,
   `4c03fcb6e63f3f07af10402bf0e5249cfc1b92b08200867b317b9b0a92b3442c`)
   and the suite re-run: **273 tests, OK**. The suite catches this
   defect class; the negative control is not decorative.
2. **Audit tamper (`test_l3_uplifts.py`, AU-9):**
   `TestVerifyChain::test_negative_control_2_mutated_entry_fails_at_index_1`
   — a clean log verifies `(True, None)`; mutating a stored entry in
   place (`log._entries[1]["actor"] = "mallory"`) makes
   `verify_chain()` report `(False, 1)` — the exact index. Companion
   tests detect a stripped `hash` field and a rewritten `prev_hash`
   (both at their own index), an edited JSONL line after reload
   (`TestHashChainPersistence`, `(False, 1)`), and the same tamper
   reported over HTTP by `GET /audit/verify`
   (`first_bad_index == 1`).

## Group 5 test adaptations (complete list)

Every copied Group 5 test passes as-is except these deliberate,
uplift-driven changes:

1. **`test_audit.py` — two exact key-set assertions relaxed to
   supersets.** `test_record_and_entries_roundtrip` and
   `test_file_backed_log_writes_jsonl` asserted audit entries carry
   *exactly* `{ts, actor, action, target, details}`. Uplift (a) adds
   `seq` / `prev_hash` / `hash` to every entry, so the assertions now
   require the original five keys (plus the three chain keys in the
   first test) as subsets. No other audit assertions changed — the
   original keys and values are unchanged, per the uplift spec.
2. **`test_access.py` — role-set test extended.**
   `test_roles_are_exactly_admin_member_viewer` became
   `test_roles_are_exactly_admin_member_viewer_auditor`: uplift (f)
   adds the `auditor` role to `PERMISSIONS` / `ROLES`. All existing
   per-role permission assertions are unchanged (existing roles'
   permissions did not move — also pinned by a new test in
   `test_l3_uplifts.py`).
3. **`accounting_helpers.py` — additive only.** Added
   `AUDITOR = User("dana", "auditor")` and the `"dana": "auditor"`
   entry in `USERS_REGISTRY`, mirroring the new demo user. No existing
   helper, user, or dataset changed; `test_service.py` (which consumes
   the registry) needed no edits — its authentication-failure counts
   per username stay below the new default lockout threshold (max 1
   per user per class server; permission denials are successful
   authentications and never counted), so no lockout trips.
4. **`test_main_cli.py` — additive only.** One new test class
   (`TestCommandLineUplifts`) spawns the CLI with the new flags and
   the dana demo user; the original CLI test is byte-identical.

No other Group 5 test file was modified (`test_books.py`,
`test_budgets.py`, `test_expenses.py`, `test_invoices.py`,
`test_ledger.py`, `test_negative_control.py`,
`test_reconciliation.py`, `test_reports.py`, `test_service.py` and
`tests/__init__.py` are byte-identical to Group 5).

## Interpretation notes

Inherited from Group 5 and still in force:

- Audit `details` defaults are accepted as `None` or `{}`.
- Over HTTP, statuses the contract does not pin (member add and the
  state-transition POSTs) are accepted as 200 or 201; creation
  endpoints pinned to 201 are asserted as 201, and auth failures are
  asserted as exactly 401.
- `GET /books` over HTTP is accepted either as the pinned
  `{"books": [...]}` wrapper or as a bare list; the wrappers the
  contract pins (`/entries` → `{"entries": [...]}`, `/audit` →
  `{"entries": [...]}`) are asserted with those wrappers.
- Store-level role enforcement is tested with `User` actors only; a
  plain-string actor carries identity but no role, so role enforcement
  for string actors belongs to the service layer.
- Report row order is not asserted positionally except where the
  contract pins it (account activity is in entry creation order).

L3-specific notes:

- `since` / `until` in `AuditLog.query` (and `GET /audit`) are ISO
  strings compared lexicographically against the entry `ts` string,
  inclusive on both ends — the unit query tests pin stored timestamps
  to fixed values (after recording, so those particular entries are
  not expected to verify) so the windows are deterministic.
- `GET /audit` keeps the Group 5 handler convention: the entries are
  read (or the query is run) *before* the handler appends its own
  `audit_read` entry, so a response never contains its own read.
  `GET /audit/verify` likewise reads the entry count *before*
  appending its `audit_read` entry; the endpoint test asserts against
  the pre-request length.
- Lockout (AC-7) counts only authentication failures for a *named*
  username (unknown user or role mismatch). Missing-header
  (anonymous) attempts and permission denials (403 after a successful
  authentication) are not counted.
- The AU-5 tests break the JSONL path mid-flight by replacing the file
  with a directory of the same name, so the append raises
  `IsADirectoryError` (an `OSError`) deterministically on any platform;
  healing removes the directory so the next append recreates the file.
  An in-memory log (no path) has no write to fail and never raises
  `AuditWriteError`.
