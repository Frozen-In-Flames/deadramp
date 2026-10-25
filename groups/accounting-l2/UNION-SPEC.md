# Union Spec — Accounting, CMMC L2 (DeadRamp Phase 2, Group 5)

The merged functional spec for the fifth sibling group built so far:
**21 forks**, category **Accounting**, CMMC tier **L2** (every member
is FedRAMP **Moderate** in `forks.json` — verified, so the group is
single-tier and the merge takes the group baseline in full, per Merge
Rule 2). The member list in `forks.json` was reconciled against
`MAP.md`'s "Accounting — L2 (21)" section: **zero diffs**.

Per-fork spec sheets: [`specs/specs.json`](specs/specs.json) — 21
entries, each with the offering's full public marketplace description
and its function claims tagged from that description, every claim
carrying the source sentence as evidence. Sources: GSA FedRAMP
Marketplace dataset (cached at `../../raw/data_dump.json`, produced
by the General Services Administration, last change 2026-10-22),
product records joined by FedRAMP ID. No live fetching was needed:
all 21 descriptions were present in the cached dataset.

## How functions were counted

A fixed 26-function taxonomy for this category was matched against
each offering's own public description. A function is claimed for a
fork **only** when the description contains matching text; the
matching sentence is stored as the claim's evidence in the spec
sheet. All 21 offerings carry at least one tagged claim (123 claims
total), so no sibling is silent — but two are thin: BlackLine
Government Solution carries 1 claim (its entire description is one
sentence, about the financial close process) and Reactor carries 1
claim (cryptocurrency investigation, an out-of-center domain kept as
its own tail family rather than forced into an accounting bucket).
Counts below are therefore a **floor**, not a ceiling, on what these
products do.

Wording-artifact corrections applied to the matcher are recorded in
`scratch/extract.py` (eleven of them). Three matter for reading this
spec:

- **No sibling says "general ledger", "bookkeeping", "double-entry",
  "payable", or "receivable".** Grep across all 21 descriptions finds
  zero occurrences. The `accounting_core` family (8 siblings) rests on
  the words "accounting", "financial management", and "federal
  financials". The double-entry journal in the Core below is included
  as the *defining mechanism* of that claim family — double-entry is
  what the word "accounting" names, the way every meeting sibling in
  Group 2 presupposed scheduling — and the spec says so plainly
  rather than pretending a sibling used the term. Standalone
  payables/receivables families had no textual support and were not
  invented; invoicing (5) and payments (3) carry their own claims.
- The broad `integrat\w+` pattern inherited from Group 2 means a few
  `api_integration` / `forecasting_epm` evidence sentences name
  complementary sibling services or suite-level phrasing rather than
  the product's own module. The evidence is stored verbatim in the
  spec sheets, so each such claim is auditable as-is.
- "Budget" alone does not tag budgeting (it appears in an OMB
  document title in one description); expense tagging requires
  expense-management phrasing, not idioms like "time and expense of
  adjusting".

## Money representation (a stated choice)

All monetary values in this build are **integer cents**. Every amount
field is named `*_cents` and must be a Python `int` — booleans are
rejected, and floats are rejected even when integral, so no binary
floating-point value can ever enter a total. All arithmetic (line
amounts, invoice totals, balances, statements) is integer arithmetic
and therefore exact by construction. Display formatting is the
caller's problem; the build stores and returns cents.

## Function ranking — all 21 siblings

| # | Function | Siblings claiming | Share | Disposition in this build |
|---|---|---:|---:|---|
| 1 | APIs, integrations & interoperability | 13 | 62% | **Core** (the service is API-first) |
| 2 | Financial reporting & statements | 12 | 57% | **Core** |
| 3 | Workflow & approvals | 12 | 57% | **Core** (the approval state machine shared by entries, invoices, expenses, with separation of duties) |
| 4 | AI, analytics & business intelligence | 9 | 43% | Extended (the reporting in Core is exact computed statements, not AI/BI analytics — stated plainly) |
| 5 | Reconciliation, settlement & financial close | 8 | 38% | **Core** |
| 6 | Core accounting & financial management | 8 | 38% | **Core** (chart of accounts + double-entry journal; see the wording note above) |
| 7 | Project, program & portfolio management | 7 | 33% | Extended (domain project accounting runs on top of a ledger substrate; this build is that substrate) |
| 8 | Budgeting, planning & cost management | 6 | 29% | **Core** (budgets per account per period, budget-vs-actual) |
| 9 | Audit trail & audit management | 6 | 29% | **Core** (the append-only audit log; audit-*management* workbenches are Extended, see below) |
| 10 | Risk management & internal controls | 6 | 29% | Extended (separation of duties, approval-required posting, and the audit trail in Core are the internal-controls seed; no risk register or GRC module is claimed) |
| 11 | Invoicing & billing | 5 | 24% | **Core** |
| 12 | Access control & authentication | 4 | 19% | **Core** (L2 baseline hooks) |
| 13 | Fixed assets, property & fleet management | 3 | 14% | Extended (an asset *account* in the chart is not an asset register or depreciation engine) |
| 14 | Payment processing, purchase cards & disbursements | 3 | 14% | **Core** (recording payments and applying them to invoices; no card networks or payment gateways — stated plainly) |
| 15 | Expense management & travel | 3 | 14% | **Core** (expense records with approval; travel *booking* is not included) |
| 16 | Records, document management & retention | 3 | 14% | Extended (the audit trail in Core is the seed; retention policies are not implemented) |
| 17 | Forecasting & enterprise performance management (EPM) | 3 | 14% | Extended |
| 18 | Supply chain, warehouse & logistics | 3 | 14% | Extended (domain operations of three siblings, outside an accounting core) |
| 19 | Grants, federal aid & GovCon accounting | 2 | 10% | Extended (GovCon/DCAA-specific compliance and grants lifecycle are domain layers on the ledger) |
| 20 | Cryptocurrency & blockchain investigation | 1 | 5% | Extended (one sibling's domain entire; not an accounting function) |
| 21 | Time tracking & scheduling | 1 | 5% | Extended (one sibling's domain; labor hours are an input to accounting, not part of this core) |
| 22 | Electronic & digital signatures | 1 | 5% | Extended |
| 23 | Payroll & labor | 1 | 5% | Extended |
| 24 | Tax reporting & support | 1 | 5% | Extended |
| 25 | Encryption | 1 | 5% | Platform note (TLS supported; see baseline section) |
| 26 | Forensic accounting & financial investigation | 1 | 5% | Extended |

**Differences are preserved, not averaged away**: the long tail above
(cryptocurrency investigation, forensic accounting, supply chain,
time tracking, e-signature, GovCon specifics) is the record of how
the siblings differ. Each Extended function names the claim family
and its sibling count; the per-fork spec sheets name which siblings
claim it.

## The Core — what the merged build implements (13 functions)

One coherent, standards-based accounting service that every sibling's
platform presupposes, built clean-room from this spec:

1. **Books & members** — named books (the fiscal container: one
   organization's accounts and records) with an owner, a member list,
   and provenance. Membership is the boundary every other core
   function enforces.
2. **Chart of accounts** — accounts inside a book, each with a code
   (unique per book), a name, and a type: `asset`, `liability`,
   `equity`, `revenue`, or `expense`. The type fixes the account's
   normal-balance direction used by every report.
3. **Double-entry journal & ledger posting** — journal entries of
   debit/credit lines against chart accounts. Every entry must
   balance (total debits equal total credits, in exact integer cents)
   or it is rejected whole. Entries are drafted, submitted, and
   **approved by someone other than their creator** (separation of
   duties) before they post; only posted entries touch the ledger,
   the balances, and the reports. A posted entry is never edited or
   voided — the standard correction is a reversing entry.
4. **Invoicing & billing** — invoices with line items (description,
   quantity, unit price in cents); line amounts and the invoice total
   are computed by the build, never trusted from the caller. Invoices
   run the same approval machine and become `issued` on approval.
5. **Payments** — payments recorded against an issued invoice and
   applied to its balance; partial payments are allowed, overpayment
   is rejected, and an invoice whose payments reach its total becomes
   `paid`.
6. **Expenses** — expense records (date, category, description,
   amount in cents) running the same approval machine; an approved
   expense can be marked reimbursed.
7. **Budgets** — a budget per book per fiscal period (`YYYY-MM`):
   planned cents per account. Setting a budget for a period that
   already has one replaces its lines. **Budget-vs-actual** compares
   planned amounts against posted ledger movement for the period.
8. **Reconciliation & period close** — an account can be reconciled
   for a period: the build computes its book balance through the end
   of that period and records the difference against a stated
   expected balance. Closing a period locks the ledger for that
   period: no entry dated in it can be created or posted afterward.
9. **Financial reporting** — computed from posted entries only:
   **trial balance** (per-account debit/credit columns that must
   total equal), **income statement** for a period (revenue, expenses,
   net income), **balance sheet** cumulative through a period (assets,
   liabilities, equity, plus cumulative net income; the sheet must
   balance, and the build computes the `balanced` flag honestly from
   the numbers rather than asserting it), and per-account **balance**
   and **activity** (the account's posted lines, chronological).
10. **Workflow & approvals** — the state machine shared by entries,
    invoices, and expenses: `draft → pending →` terminal state
    (`posted` / `issued` / `approved`), with `rejected` returning the
    object to an editable-by-void state and `void` available from
    `draft`/`rejected` to the creator, the book owner, or a platform
    admin. Approval and rejection require an actor other than the
    object's creator (separation of duties, AC-5).
11. **API access** — every function above is exposed over a REST API
    (JSON), so the service composes with anything that speaks HTTP.
12. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced on
    every operation, layered with book membership (non-members cannot
    read or write a book's content; the platform `admin` role can).
13. **Audit log** — an append-only audit trail: every book,
    membership, account, entry, invoice, payment, expense, budget,
    reconciliation, and period-close mutation, and every denied
    attempt, recorded with actor, action, target, and UTC timestamp.

## Control baseline (traceability)

- **Group tier:** CMMC **L2** ⇔ FedRAMP **Moderate** (per
  `../../crosswalk.md`).
- **Baseline source:** NIST SP 800-53 Rev. 5 **Moderate** baseline
  (the FedRAMP Moderate tailoring), cross-walked to the 110 practices
  of NIST SP 800-171 Rev. 2 that define CMMC L2. All 21 parent forks
  sit at Moderate, so the union baseline is the Moderate baseline,
  un-diluted (Merge Rule 1) and inherited in full (Merge Rule 2).
- **Feature → control family mapping (this build):**
  - Access control (platform roles + book membership) → **AC**
    (AC-2 account management, AC-3 access enforcement, AC-6 least
    privilege), **IA** (IA-2 identification & authentication —
    identity is supplied by the embedding organization via user/role
    headers; the service ships hooks, not an identity provider).
  - Workflow & approvals → **AC-5** (separation of duties — the
    approver of an entry, invoice, or expense is never its creator,
    enforced in the store).
  - Audit log → **AU** (AU-2 event logging, AU-3 content of audit
    records, AU-6 audit review, AU-9 protection of audit
    information — append-only store, admin-only read).
    Reconciliation records and period closes are audit records in the
    same trail.
  - Journal / invoices / expenses / payments / budgets → **SI**
    (SI-10 information input validation — malformed input, including
    any non-integer or unbalanced amount, is rejected whole, never
    partially applied) and **SC** (SC-8 transmission confidentiality
    — the server runs over TLS when a certificate is configured;
    encryption at rest is a deployment-layer control, stated plainly,
    not claimed here).
- **Caveat, same as the crosswalk's:** this mapping states which
  baseline families the build's features answer to. It is not a
  FedRAMP authorization and not a CMMC certification, and it does not
  claim either.

## Implementation contract (what `src/` and `tests/` are built against)

Python 3, **standard library only**. Package `accounting` under
`src/`, runnable and testable with `PYTHONPATH=src`. Ids are
sequential per object type with fixed prefixes (`book-`, `acct-`,
`je-`, `inv-`, `pay-`, `exp-`, `bud-`, `rec-`); a failed operation
consumes no id and changes nothing. All timestamps are UTC ISO-8601.
All money is integer cents (see the money section above). Dates are
ISO calendar dates (`YYYY-MM-DD`); a fiscal period is the string
`YYYY-MM` derived from a date, or supplied directly and validated.

- `accounting/errors.py` — `AccountingError`, `ValidationError`,
  `NotFoundError`, `PermissionDenied` (all deriving from
  `AccountingError`).
- `accounting/access.py` — `User(name, role)`; roles
  `admin|member|viewer`; actions `read, create_book, enter, submit,
  approve, pay, close, manage_members, audit_read, admin`.
  `PERMISSIONS`: admin ⊇ all ten; member = {read, create_book,
  enter, submit, approve, pay, close}; viewer = {read}.
  `permissions_for(role)`, `can(user, action)`, `require(user,
  action)` raising `PermissionDenied`.
- `accounting/audit.py` — `AuditLog(path=None)`; `.record(actor,
  action, target, details=None)`; `.entries()` returns entry dicts
  with keys `ts, actor, action, target, details`. Append-only;
  optional JSONL file persistence; reloads an existing file on
  construction.
- `accounting/store.py` — `AccountingStore(audit=None)`. The store
  records every successful mutation to its audit log (when one is
  attached) with the action names used below; the HTTP layer records
  denials and `audit_read` only, never duplicating store records.
  Two boundaries on every book-scoped operation: the actor must be a
  book member or hold the platform `admin` role, else
  `PermissionDenied`; and the operation's role permission is required
  (enforced via the same User-like pattern as the sibling groups: a
  plain string actor carries identity but no role, so role enforcement
  for those happens in the service layer). Validation always precedes
  mutation: a failed operation changes nothing, consumes no id.
  Amounts: any amount that is not an `int` (booleans included) raises
  `ValidationError`; negative amounts raise `ValidationError` except
  where a method says otherwise. Methods:
  - `create_book(name, actor)` → `{id, name, owner, members,
    closed_periods, created_by, created_utc}`; the creator is owner
    and first member; `closed_periods` starts empty. Audits
    `book_create`.
  - `list_books(actor)` → book dicts the actor may see (member of,
    or platform admin). `get_book(book_id, actor)` → one dict
    (`NotFoundError`, or `PermissionDenied` for a non-member).
  - `add_member(book_id, username, actor)` → updated book dict. Only
    the book owner or a platform admin may add; adding an existing
    member raises `ValidationError`. Audits `member_add`.
  - `create_account(book_id, code, name, account_type, actor)`
    (action `enter`) → `{id, book_id, code, name, type, active,
    created_by, created_utc}` with `active` True. `code` must be a
    non-empty string unique within the book (duplicate →
    `ValidationError`); `account_type` must be one of `asset`,
    `liability`, `equity`, `revenue`, `expense`. Audits
    `account_create`. `list_accounts(book_id, actor)` in creation
    order; `get_account(book_id, account_id, actor)` (an id from
    another book → `NotFoundError`).
  - `create_entry(book_id, date, memo, lines, actor)` (action
    `enter`) → `{id, book_id, date, period, memo, lines,
    total_cents, status, created_by, created_utc, submitted_by,
    approved_by, posted_utc}`. `date` must be a valid ISO date;
    `period` is `date[:7]` and must not be in the book's
    `closed_periods`. `memo` is a string (default `""`). `lines` is
    a list of at least two dicts `{account_id, debit_cents,
    credit_cents}` (a missing side counts as 0); every `account_id`
    must name an account in this book (else `ValidationError`);
    each line must have exactly one side positive and the other
    zero; all amounts valid cents; total debits must equal total
    credits and be positive — **an unbalanced entry raises
    `ValidationError` and stores nothing**. Stored lines are
    normalized to always carry both `debit_cents` and `credit_cents`.
    Initial status `draft`; `submitted_by`/`approved_by`/
    `posted_utc` start as None. Audits `entry_create`.
    `get_entry(book_id, entry_id, actor)`;
    `list_entries(book_id, actor, status=None)` in creation order
    (an unknown `status` filter → `ValidationError`).
  - `submit_entry(book_id, entry_id, actor)` (action `submit`):
    status `draft` or `rejected` → `pending`, sets `submitted_by`.
    Audits `entry_submit`. `approve_entry(book_id, entry_id, actor)`
    (action `approve`): status `pending` → `posted`; the actor's
    name must differ from `created_by` (else `PermissionDenied` —
    separation of duties); the entry's period must not be closed
    (else `ValidationError`); sets `approved_by` and `posted_utc`.
    Audits `entry_post`. `reject_entry(book_id, entry_id, actor)`
    (action `approve`): status `pending` → `rejected`, same SoD
    rule. Audits `entry_reject`. `void_entry(book_id, entry_id,
    actor)` (action `enter`): status `draft` or `rejected` →
    `void`; only the creator, the book owner, or a platform admin.
    Audits `entry_void`.
  - `create_invoice(book_id, customer, date, due_date, lines,
    actor)` (action `enter`) → `{id, book_id, customer, date,
    due_date, lines, total_cents, paid_cents, status, created_by,
    created_utc, submitted_by, approved_by, issued_utc}`. `customer`
    a non-empty string; both dates valid ISO dates, `due_date` not
    before `date`. `lines` is a list of at least one dict
    `{description, quantity, unit_price_cents}`: description
    non-empty, `quantity` an int ≥ 1, `unit_price_cents` an int
    ≥ 0; each stored line gains `amount_cents =
    quantity * unit_price_cents`, computed here; `total_cents` is
    the sum of line amounts and must be positive. `paid_cents`
    starts 0; status `draft`. Audits `invoice_create`.
    `get_invoice(book_id, invoice_id, actor)`;
    `list_invoices(book_id, actor, status=None)`.
  - `submit_invoice` / `approve_invoice` / `reject_invoice` /
    `void_invoice` — the same state machine as entries, with
    `approve` moving `pending` → `issued` (sets `approved_by`,
    `issued_utc`; audits `invoice_issue`), audits `invoice_submit`,
    `invoice_reject`, `invoice_void`. `void_invoice` additionally
    accepts status `issued` when `paid_cents` is 0.
  - `record_payment(book_id, invoice_id, amount_cents, date, actor,
    method="")` (action `pay`) → `{id, book_id, invoice_id,
    amount_cents, date, method, created_by, created_utc}`. The
    invoice must be in this book and in status `issued` (else
    `ValidationError`); `amount_cents` a positive int not exceeding
    `total_cents - paid_cents` (else `ValidationError`); `date` a
    valid ISO date. Applies the payment: the invoice's `paid_cents`
    increases, and reaching the total moves the invoice to `paid`.
    Audits `payment_record`. `list_payments(book_id, actor,
    invoice_id=None)`.
  - `create_expense(book_id, date, category, description,
    amount_cents, actor)` (action `enter`) → `{id, book_id, date,
    category, description, amount_cents, status, created_by,
    created_utc, submitted_by, approved_by}`. Date valid; `category`
    and `description` non-empty strings; `amount_cents` a positive
    int. Status `draft`. Audits `expense_create`.
    `get_expense(book_id, expense_id, actor)`;
    `list_expenses(book_id, actor, status=None)`.
    `submit_expense` / `approve_expense` (→ `approved`) /
    `reject_expense` / `void_expense` — the same state machine;
    audits `expense_submit`, `expense_approve`, `expense_reject`,
    `expense_void`. `reimburse_expense(book_id, expense_id, actor)`
    (action `pay`): status `approved` → `reimbursed`. Audits
    `expense_reimburse`.
  - `set_budget(book_id, period, lines, actor)` (action `enter`) →
    `{id, book_id, period, lines, total_cents, created_by,
    created_utc, updated_utc}`. `period` must be a valid `YYYY-MM`.
    `lines` is a list of at least one dict `{account_id,
    amount_cents}`; every account must exist in this book; amounts
    are ints ≥ 0; a repeated account in one call →
    `ValidationError`. One budget per (book, period): if one exists,
    its lines and total are replaced, its `id`, `created_by`, and
    `created_utc` are kept, and `updated_utc` is refreshed. Audits
    `budget_set`. `get_budget(book_id, period, actor)` → the budget
    dict (`NotFoundError` if none was set for that period).
  - `budget_vs_actual(book_id, period, actor)` (action `read`) →
    `{book_id, period, lines, total_budgeted_cents,
    total_actual_cents, total_variance_cents}`; requires a budget
    for the period (else `NotFoundError`). Each line: `{account_id,
    code, name, type, budgeted_cents, actual_cents,
    variance_cents}`. `actual_cents` is the account's posted movement
    within the period in its normal-balance direction (asset and
    expense: debits − credits; liability, equity, revenue:
    credits − debits). `variance_cents = budgeted_cents -
    actual_cents`.
  - `trial_balance(book_id, actor, period=None)` (action `read`) →
    `{book_id, period, accounts, total_debits_cents,
    total_credits_cents, balanced}`. Posted entries only (all
    periods, or only the given period). Per account, net = total
    debits − total credits across the selected entries; a positive
    net appears as `debit_cents`, a negative net as `credit_cents`
    (its absolute value), a zero net omits the account. Each account
    row: `{account_id, code, name, type, debit_cents,
    credit_cents}`. `balanced` is `total_debits_cents ==
    total_credits_cents`, computed from the rows.
  - `account_balance(book_id, account_id, actor, period=None)`
    (action `read`) → `{account_id, book_id, period, debit_cents,
    credit_cents, balance_cents}`: raw posted totals for the account
    (optionally within one period) and the normal-direction signed
    balance (asset/expense: debits − credits; liability/equity/
    revenue: credits − debits).
  - `account_activity(book_id, account_id, actor, period=None)`
    (action `read`) → `{account_id, book_id, period, lines}`:
    the account's posted lines in entry creation order, each
    `{entry_id, date, period, memo, debit_cents, credit_cents}`.
  - `income_statement(book_id, period, actor)` (action `read`) →
    `{book_id, period, revenue, total_revenue_cents, expenses,
    total_expense_cents, net_income_cents}`. `period` is required
    and must be valid. Revenue rows are revenue-type accounts with
    non-zero movement in the period, `amount_cents` = credits −
    debits; expense rows likewise with debits − credits; each row
    `{account_id, code, name, amount_cents}`. `net_income_cents =
    total_revenue_cents - total_expense_cents`.
  - `balance_sheet(book_id, actor, through_period=None)` (action
    `read`) → `{book_id, through_period, assets,
    total_assets_cents, liabilities, total_liabilities_cents,
    equity, total_equity_cents, net_income_cents,
    total_liabilities_equity_cents, balanced}`. Cumulative over
    posted entries with `period <= through_period` (all entries when
    None). Asset/liability/equity rows are accounts of that type
    with non-zero cumulative normal-direction balance, each
    `{account_id, code, name, amount_cents}`. `net_income_cents` is
    cumulative revenue minus cumulative expenses over the same
    entries. `total_liabilities_equity_cents =
    total_liabilities_cents + total_equity_cents +
    net_income_cents`. `balanced` is `total_assets_cents ==
    total_liabilities_equity_cents`, computed, not asserted.
  - `reconcile_account(book_id, account_id, period,
    expected_balance_cents, actor)` (action `close`) → `{id,
    book_id, account_id, period, book_balance_cents, expected_cents,
    difference_cents, matched, created_by, created_utc}`. `period`
    valid `YYYY-MM`; `expected_balance_cents` any int.
    `book_balance_cents` is the account's cumulative normal-direction
    balance over posted entries with `period <=` the given period.
    `difference_cents = book_balance_cents - expected_cents`;
    `matched` is `difference_cents == 0`. Audits
    `reconciliation_create`.
  - `close_period(book_id, period, actor)` (action `close`) →
    `{book_id, period, closed_by, closed_utc}`. `period` valid;
    closing an already-closed period → `ValidationError`. Adds the
    period to the book's `closed_periods` (kept sorted). After a
    period is closed, `create_entry` with a date in it and
    `approve_entry` on an entry in it raise `ValidationError`.
    Audits `period_close`.
- `accounting/service.py` — `make_server(host, port, store, audit,
  users)` → `http.server.ThreadingHTTPServer`; `users` maps name →
  role. Auth via `X-User` / `X-Role` headers (the role must match
  the registry; unknown user or mismatched role → 401). Errors are
  JSON `{error}` with 400/401/403/404 as applicable; denied attempts
  (401 and 403) are audited with the action name suffixed `:denied`,
  and no stack trace is ever returned. Endpoints:
  - `GET /health` (no auth) → `{"status": "ok"}`
  - `GET /audit` (audit_read) → `{"entries": [...]}`
  - `GET /books` (read) → `{"books": [...]}`;
    `POST /books` `{name}` (create_book) → 201 book dict
  - `GET /books/{id}` (read)
  - `POST /books/{id}/members` `{username}` (any authenticated
    user; the store enforces owner-or-admin) → book dict
  - `GET /books/{id}/accounts` (read) → `{"accounts": [...]}`;
    `POST /books/{id}/accounts` `{code, name, type}` (enter) → 201
  - `GET /books/{id}/accounts/{aid}` (read)
  - `GET /books/{id}/accounts/{aid}/balance?period=` (read)
  - `GET /books/{id}/accounts/{aid}/activity?period=` (read)
  - `POST /books/{id}/accounts/{aid}/reconcile` `{period,
    expected_balance_cents}` (close) → 201
  - `GET /books/{id}/entries?status=` (read) → `{"entries":
    [...]}`; `POST /books/{id}/entries` `{date, memo?, lines}`
    (enter) → 201
  - `GET /books/{id}/entries/{eid}` (read)
  - `POST /books/{id}/entries/{eid}/submit` (submit);
    `POST /books/{id}/entries/{eid}/approve` (approve);
    `POST /books/{id}/entries/{eid}/reject` (approve);
    `POST /books/{id}/entries/{eid}/void` (enter) → updated entry
  - `GET /books/{id}/invoices?status=` (read) → `{"invoices":
    [...]}`; `POST /books/{id}/invoices` `{customer, date,
    due_date, lines}` (enter) → 201
  - `GET /books/{id}/invoices/{iid}` (read)
  - `POST /books/{id}/invoices/{iid}/submit` (submit);
    `/approve` (approve); `/reject` (approve); `/void` (enter)
  - `GET /books/{id}/payments?invoice_id=` (read) →
    `{"payments": [...]}`; `POST /books/{id}/invoices/{iid}/payments`
    `{amount_cents, date, method?}` (pay) → 201 payment dict
  - `GET /books/{id}/expenses?status=` (read) → `{"expenses":
    [...]}`; `POST /books/{id}/expenses` `{date, category,
    description, amount_cents}` (enter) → 201
  - `GET /books/{id}/expenses/{xid}` (read)
  - `POST /books/{id}/expenses/{xid}/submit` (submit);
    `/approve` (approve); `/reject` (approve); `/void` (enter);
    `/reimburse` (pay)
  - `PUT /books/{id}/budgets/{period}` `{lines}` (enter) → budget
    dict; `GET /books/{id}/budgets/{period}` (read);
    `GET /books/{id}/budgets/{period}/vs-actual` (read)
  - `GET /books/{id}/reports/trial-balance?period=` (read);
    `GET /books/{id}/reports/income-statement?period=` (read;
    a missing `period` → 400);
    `GET /books/{id}/reports/balance-sheet?through_period=` (read)
  - `POST /books/{id}/periods/{period}/close` (close) → close dict
- `accounting/__main__.py` — `python -m accounting serve --host
  --port [--audit-log PATH] [--certfile --keyfile]` with demo users
  `alice=admin, bob=member, carol=viewer` (documented as demo
  identities; production identity is the embedding organization's,
  per IA-2 above).

Tests live in `tests/` (stdlib `unittest`), each test docstring
naming the core function / spec claim it traces to, and include a
**negative control**: a mutant balance check (one that computes the
debit and credit sums but never compares them, treating every entry
as balanced) whose behavior the canonical expectation is shown to
reject — an unbalanced entry must raise `ValidationError` from the
real store and store nothing, and the mutant is demonstrated to wave
it through — proving the suite catches that defect class rather than
merely passing. The negative control must additionally be
**mutation-verified**: patching the real balance check in `src/`
with the mutant must make the suite fail; the run and its result are
recorded in `tests/README.md`.

## Coverage statement (for this build)

- Specs: 21 / 21 forks spec'd.
- Core: 13 core functions implemented, each with tracing tests.
- Extended: 14 functions specified and ranked, **not** implemented
  in this build (AI/analytics & BI, project/program/portfolio
  management, risk register & GRC beyond the SoD/audit seed,
  fixed-asset registers, records retention beyond the audit seed,
  forecasting & EPM, supply chain, GovCon/grants specifics, crypto
  investigation, time tracking, e-signature, payroll, tax support,
  forensic investigation); encryption is a platform note (TLS when a
  certificate is configured; at rest is a deployment-layer control).
  Audit *management* (TeamMate-style workbenches: audit plans,
  workpapers, findings) is likewise specified by the `audit` family's
  claims but is not this core; the core carries the audit *trail*.
