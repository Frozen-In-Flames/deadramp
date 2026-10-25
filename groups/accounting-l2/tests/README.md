# Tests — Accounting L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/accounting-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 219 tests
```

Status at delivery: **219 tests, OK** against the implementation in
`../src/`. (Run exactly as above: helpers are imported as a top-level
module from the tests directory and `tests/__init__.py` is empty by
design, so package-mode discovery with `-t .` is not the supported
entry point for this group.)

## Layout

| File | Covers (UNION-SPEC Core) |
|---|---|
| `test_access.py` | 12 Access control — exact permission matrix for admin/member/viewer (admin all ten actions; member {read, create_book, enter, submit, approve, pay, close}; viewer {read}), `permissions_for()`, `can()`, `require()`, unknown role/action/user denied |
| `test_audit.py` | 13 Audit log — entry keys, append-only, JSONL file + reload on construction, and the store recording each mutation action (`book_create`, `member_add`, `account_create`, `entry_create`, `entry_submit`, `entry_post`, `entry_reject`, `entry_void`, `invoice_create`, `invoice_submit`, `invoice_issue`, `invoice_reject`, `invoice_void`, `payment_record`, `expense_create`, `expense_submit`, `expense_approve`, `expense_reject`, `expense_void`, `expense_reimburse`, `budget_set`, `reconciliation_create`, `period_close`) |
| `test_books.py` | 1 Books & members + 2 Chart of accounts — book creation shape/provenance incl. `closed_periods []`, `book-` id sequence, list visibility, owner-or-admin `add_member`, duplicate add → `ValidationError`, non-member get → `PermissionDenied`, failed ops consume no ids; accounts: creation shape, duplicate code in same book → `ValidationError` (same code in a different book OK), bad type → `ValidationError`, cross-book get → `NotFoundError` |
| `test_ledger.py` | 3 Double-entry journal & ledger posting + 10 Workflow & approvals — balanced entry creation shape (period derived, lines normalized, `total_cents`), unbalanced / one-line / both-sides-positive / zero-total / float / bool / unknown-account entries → `ValidationError` with nothing stored and no id consumed, draft not counted in balances, submit from draft and from rejected, approve/reject by creator → `PermissionDenied` (SoD), approve posts with `approved_by`/`posted_utc`, double approve → `ValidationError`, void from draft and rejected by creator, void of pending/posted → `ValidationError`, void by unrelated member → `PermissionDenied` |
| `test_invoices.py` | 4 Invoicing & billing + 5 Payments + 10 Workflow & approvals — computed line amounts and total (quantity × unit price, exact with large cents values), zero-quantity / negative price / `due_date` before `date` / empty lines → `ValidationError`, machine to issued, partial payment leaves issued with `paid_cents` updated, completing payment → paid, overpayment → `ValidationError` with `paid_cents` unchanged, payment on draft invoice → `ValidationError`, payment float amount → `ValidationError`, void issued-unpaid OK, void issued-with-payment → `ValidationError`, `list_payments` filtered by invoice |
| `test_expenses.py` | 6 Expenses + 10 Workflow & approvals — creation shape/validation (zero/negative/float amounts, empty category), machine to approved, reimburse from approved → reimbursed, reimburse from draft → `ValidationError`, SoD on approve |
| `test_budgets.py` | 7 Budgets — `set_budget` shape + total, replace semantics (same id, `created_utc` kept, lines replaced), duplicate account line → `ValidationError`, unknown account → `ValidationError`, `get_budget` missing period → `NotFoundError`, budget-vs-actual math (actual in normal direction for expense and revenue accounts, variance = budgeted − actual, other-period and draft/pending entries excluded) |
| `test_reports.py` | 9 Financial reporting — one coherent scenario (owner invests 100000¢, earns 50000¢, pays 20000¢ rent → Cash 130000, equity 100000, net income 30000): trial balance (balanced flag true, totals equal, debit/credit column placement by net sign, period filter), `account_balance` normal-direction signs for asset and liability, `account_activity` (posted only, chronological, per-line amounts), income statement (revenue/expense rows, net = revenue − expenses, other periods excluded), balance sheet (assets = liabilities + equity + cumulative net income, balanced true, `through_period` filter) |
| `test_reconciliation.py` | 8 Reconciliation & period close — reconcile matched (difference 0, matched true), reconcile with difference (signed difference = book − expected, matched false), `close_period` shape, closing twice → `ValidationError`, `create_entry` dated in closed period → `ValidationError`, approve of a pending entry dated in the closed period → `ValidationError` (entry stays pending), entries in open periods unaffected, book dict `closed_periods` updated |
| `test_service.py` | 11 API access — live HTTP server: `/health` without auth, 401 unknown user and role mismatch, 403 viewer creating an account (enter) and viewer approving, full flow (create book → accounts → entry → submit → approve by another user → trial balance balanced → invoice → issue → payment → invoice paid), SoD over HTTP (creator approve → 403), unbalanced entry over HTTP → 400 with no entry created, income-statement without period → 400, audit endpoint admin-only (member → 403) and denied attempts recorded with `:denied` suffix |
| `test_main_cli.py` | `python -m accounting serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `accounting_helpers.py` | Shared fixtures: demo users (ADMIN/MEMBER/VIEWER/OUTSIDER), `make_store()` building an AccountingStore + AuditLog + a book owned by MEMBER with VIEWER added as member, `make_chart()` creating the five canonical accounts (Cash asset 1000, AccountsPayable liability 2000, OwnersEquity equity 3000, ServiceRevenue revenue 4000, RentExpense expense 5000), `post_entry()` posting an entry end-to-end (create by MEMBER, submit, approve by ADMIN), `approve_entry_by_other()`, and the canonical posted-scenario builders |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
a balance check that computes the debit and credit sums but **never
compares them**, treating every entry as balanced. The traced claim,
named in the module's docstrings, is that the debits-equal-credits
invariant is the SI-10 / Core 3 integrity boundary of the ledger. For
each canonical case — (a) an unbalanced entry (debits 10000, credits
9999) and (b) an entry whose lines are individually valid but whose
total debits exceed credits by 1 cent — the test asserts three things:
the canonical expectation (`ValidationError` from the real store, with
nothing stored and no entry id consumed), that the mutant gate would
NOT raise (it waves the unbalanced entry through as "balanced"), and —
via a literal `assertRaises(AssertionError)` — that treating the
mutant's outcome as the expected outcome fails. Case (c) is the
control sanity check: a genuinely balanced entry passes both the real
store and the mutant.

## Mutation verification

VERIFIED by the coordinator (2026-10-25). The balance check in
`AccountingStore.create_entry` (`src/accounting/store.py`) was
patched from `if total_debits != total_credits or total_debits <= 0:`
to `if total_debits <= 0:` — the exact live counterpart of the
mutant in `test_negative_control.py`, computing the sums but never
comparing them — and the full suite was run: **219 tests ran, 4
failed**. The failures are exactly the defect class's surface:
`test_ledger`'s unbalanced-entry rejection, both negative-control
unbalanced cases (10000 vs 9999, and debits exceeding credits by one
cent), and `test_service`'s unbalanced-entry-over-HTTP case.
`store.py` was then restored from a pre-mutation copy (SHA-256
verified identical to the pre-mutation hash,
`fb7eff3d22b40f2f0885f7b02650f1a0bba3b4d346ff2493d3a1af67751c2274`)
and the suite re-run: **219 tests, OK**. The suite catches this
defect class; the negative control is not decorative.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite stays
tolerant of the remaining freedom:

- Audit `details` defaults are accepted as `None` or `{}`.
- Over HTTP, statuses the contract does not pin (member add and the
  state-transition POSTs: submit/approve/reject/void/reimburse) are
  accepted as 200 or 201; creation endpoints the contract does pin to
  201 are asserted as 201, and auth failures are asserted as exactly
  401 per the contract ("unknown user or mismatched role → 401").
- `GET /books` over HTTP is accepted either as the pinned
  `{"books": [...]}` wrapper or as a bare list; the list endpoints
  whose wrappers the contract pins (`/entries` → `{"entries": [...]}`,
  `/audit` → `{"entries": [...]}`) are asserted with those wrappers.
- Budget replacement: `updated_utc` is asserted present (and the id,
  `created_by`, and `created_utc` kept, per the contract), but not
  asserted strictly greater than the original — the contract does not
  pin timestamp resolution, so a same-tick refresh is acceptable.
- `permissions_for()` for an unknown role is accepted as either an
  empty permission set or a denying raise; `can()` for an unknown role
  likewise. `require()` for an unknown role must deny.
- Store-level role enforcement is tested with `User` actors only. Per
  the contract, a plain-string actor carries identity but no role, so
  role enforcement for string actors belongs to the service layer and
  is not asserted against the store.
- `reconcile_account`'s `expected_balance_cents` is treated as an
  amount under the contract's general money rule (any non-`int`,
  booleans included, raises `ValidationError`), while any `int` —
  including negative values — is accepted, per the contract's "any
  int".
- Report row order is not asserted positionally except where the
  contract pins it (account activity is in entry creation order);
  trial-balance, budget-vs-actual, and statement rows are looked up by
  `account_id`.
