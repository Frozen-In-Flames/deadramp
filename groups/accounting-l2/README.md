# Accounting L2 — merged build (Operation DeadRamp, Phase 2, Group 5)

This is the merged, clean-room implementation of the **Accounting
L2** sibling group: **21 forks** from the FedRAMP Marketplace that
share the same function (Accounting) and the same trust tier (CMMC
L2, equivalent to FedRAMP Moderate), built as one open-source service
per the group's union spec, [`UNION-SPEC.md`](UNION-SPEC.md).

It was written from the contract in that spec only: original code,
no vendor code, assets, or branding from any of the 21 sibling
offerings. Python 3, **standard library only**, no external
dependencies.

## The 13 core functions

1. **Books & members** — named books (the fiscal container: one
   organization's accounts and records) with an owner, a member
   list, and provenance. Membership is the boundary every other
   core function enforces.
2. **Chart of accounts** — accounts inside a book, each with a code
   (unique per book), a name, and a type: `asset`, `liability`,
   `equity`, `revenue`, or `expense`. The type fixes the account's
   normal-balance direction used by every report.
3. **Double-entry journal & ledger posting** — journal entries of
   debit/credit lines against chart accounts. Every entry must
   balance (total debits equal total credits) or it is rejected
   whole. Entries are drafted, submitted, and approved before they
   post; only posted entries touch the ledger, the balances, and
   the reports. A posted entry is never edited or voided — the
   correction is a reversing entry.
4. **Invoicing & billing** — invoices with line items (description,
   quantity, unit price in cents); line amounts and the invoice
   total are computed by the service, never trusted from the
   caller. Invoices run the same approval machine and become
   `issued` on approval.
5. **Payments** — payments recorded against an issued invoice and
   applied to its balance; partial payments allowed, overpayment
   rejected, an invoice whose payments reach its total becomes
   `paid`.
6. **Expenses** — expense records (date, category, description,
   amount in cents) running the same approval machine; an approved
   expense can be marked reimbursed.
7. **Budgets** — a budget per book per fiscal period (`YYYY-MM`):
   planned cents per account; setting one for an existing period
   replaces its lines. **Budget-vs-actual** compares planned
   amounts against posted ledger movement for the period.
8. **Reconciliation & period close** — an account can be
   reconciled for a period: the service computes its book balance
   through the end of that period and records the difference
   against a stated expected balance. Closing a period locks the
   ledger for it: no entry dated in it can be created or posted
   afterward.
9. **Financial reporting** — computed from posted entries only:
   trial balance (per-account debit/credit columns, `balanced`
   computed from the rows), income statement for a period,
   balance sheet cumulative through a period (with cumulative net
   income; the `balanced` flag is computed, not asserted), and
   per-account balance and activity.
10. **Workflow & approvals** — the state machine shared by
    entries, invoices, and expenses (`draft → pending →`
    `posted` / `issued` / `approved`, plus `rejected` and `void`),
    with **separation of duties**: the approver or rejecter of an
    object is never its creator.
11. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
12. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer` with a permission matrix enforced
    on every operation, layered with book membership (non-members
    cannot read or write a book's content; the platform `admin`
    role can).
13. **Audit log** — an append-only audit trail: every book,
    membership, account, entry, invoice, payment, expense, budget,
    reconciliation, and period-close mutation, and every denied
    attempt, recorded with actor, action, target, and UTC
    timestamp. Optional JSONL file persistence.

**Money is integer cents, everywhere.** Every amount field is
`*_cents` and must be an integer — booleans and floats are rejected
at the boundary, even integral floats — so all arithmetic is exact
by construction. Malformed input is rejected with a validation
error and leaves the store completely unchanged (no partial
application, no id consumed). Ids are sequential per object type:
`book-`, `acct-`, `je-`, `inv-`, `pay-`, `exp-`, `bud-`, `rec-`.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m accounting serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`). A startup line is printed once the server is listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, create_book, enter, submit, approve, pay, close, manage_members, audit_read, admin |
| `bob`   | member  | read, create_book, enter, submit, approve, pay, close |
| `carol` | viewer  | read |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/health` | none | `{"status": "ok"}` |
| GET | `/audit` | audit_read | `{"entries": [...]}` |
| GET | `/books` | read | List books visible to the caller → `{"books": [...]}` |
| POST | `/books` | create_book | Body `{"name"}` → 201 book dict |
| GET | `/books/{id}` | read | One book dict |
| POST | `/books/{id}/members` | any authenticated (store enforces owner-or-admin) | Body `{"username"}` → book dict |
| GET | `/books/{id}/accounts` | read | List accounts → `{"accounts": [...]}` |
| POST | `/books/{id}/accounts` | enter | Body `{"code", "name", "type"}` → 201 account dict |
| GET | `/books/{id}/accounts/{aid}` | read | One account dict |
| GET | `/books/{id}/accounts/{aid}/balance?period=` | read | Raw posted totals + normal-direction balance |
| GET | `/books/{id}/accounts/{aid}/activity?period=` | read | The account's posted lines, chronological |
| POST | `/books/{id}/accounts/{aid}/reconcile` | close | Body `{"period", "expected_balance_cents"}` → 201 reconciliation dict |
| GET | `/books/{id}/entries?status=` | read | List journal entries → `{"entries": [...]}` |
| POST | `/books/{id}/entries` | enter | Body `{"date", "memo"?, "lines"}` → 201 entry dict |
| GET | `/books/{id}/entries/{eid}` | read | One entry dict |
| POST | `/books/{id}/entries/{eid}/submit` | submit | → updated entry dict |
| POST | `/books/{id}/entries/{eid}/approve` | approve | → posted entry dict (approver ≠ creator) |
| POST | `/books/{id}/entries/{eid}/reject` | approve | → rejected entry dict |
| POST | `/books/{id}/entries/{eid}/void` | enter | → voided entry dict |
| GET | `/books/{id}/invoices?status=` | read | List invoices → `{"invoices": [...]}` |
| POST | `/books/{id}/invoices` | enter | Body `{"customer", "date", "due_date", "lines"}` → 201 invoice dict |
| GET | `/books/{id}/invoices/{iid}` | read | One invoice dict |
| POST | `/books/{id}/invoices/{iid}/submit` | submit | → updated invoice dict |
| POST | `/books/{id}/invoices/{iid}/approve` | approve | → issued invoice dict |
| POST | `/books/{id}/invoices/{iid}/reject` | approve | → rejected invoice dict |
| POST | `/books/{id}/invoices/{iid}/void` | enter | → voided invoice dict |
| GET | `/books/{id}/payments?invoice_id=` | read | List payments → `{"payments": [...]}` |
| POST | `/books/{id}/invoices/{iid}/payments` | pay | Body `{"amount_cents", "date", "method"?}` → 201 payment dict |
| GET | `/books/{id}/expenses?status=` | read | List expenses → `{"expenses": [...]}` |
| POST | `/books/{id}/expenses` | enter | Body `{"date", "category", "description", "amount_cents"}` → 201 expense dict |
| GET | `/books/{id}/expenses/{xid}` | read | One expense dict |
| POST | `/books/{id}/expenses/{xid}/submit` | submit | → updated expense dict |
| POST | `/books/{id}/expenses/{xid}/approve` | approve | → approved expense dict |
| POST | `/books/{id}/expenses/{xid}/reject` | approve | → rejected expense dict |
| POST | `/books/{id}/expenses/{xid}/void` | enter | → voided expense dict |
| POST | `/books/{id}/expenses/{xid}/reimburse` | pay | → reimbursed expense dict |
| PUT | `/books/{id}/budgets/{period}` | enter | Body `{"lines"}` → budget dict (create-or-replace) |
| GET | `/books/{id}/budgets/{period}` | read | One budget dict |
| GET | `/books/{id}/budgets/{period}/vs-actual` | read | Budget lines with actuals and variances |
| GET | `/books/{id}/reports/trial-balance?period=` | read | Trial balance dict |
| GET | `/books/{id}/reports/income-statement?period=` | read | Income statement dict (`period` required) |
| GET | `/books/{id}/reports/balance-sheet?through_period=` | read | Balance sheet dict |
| POST | `/books/{id}/periods/{period}/close` | close | → close dict |

Book dicts are `{id, name, owner, members, closed_periods,
created_by, created_utc}` with sequential ids `book-1`, `book-2`,
…; the other object types follow the same pattern with their own
prefixes (see `UNION-SPEC.md` for every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in
`UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

Status at delivery: **219 tests, OK**, including a
mutation-verified negative control on the debits-equal-credits
invariant (see `tests/README.md`).

## Control-family mapping (summary)

Per `UNION-SPEC.md`, against the NIST SP 800-53 Rev. 5 Moderate
baseline cross-walked to the NIST SP 800-171 Rev. 2 practices that
define CMMC L2:

- **AC / IA** — access control (platform roles + book membership):
  AC-2 (account management), AC-3 (access enforcement), AC-6
  (least privilege); IA-2 (identification & authentication —
  identity is supplied by the embedding organization via user/role
  headers; this service ships hooks, not an IdP).
- **AC-5** — separation of duties: the approver of an entry,
  invoice, or expense is never its creator, enforced in the store.
- **AU** — audit log: AU-2 (event logging), AU-3 (content of audit
  records), AU-6 (audit review), AU-9 (protection of audit
  information — append-only store, audit-read restricted to the
  `audit_read` permission).
- **SI / SC** — journal / invoices / expenses / payments / budgets:
  SI-10 (information input validation — malformed input, including
  any non-integer or unbalanced amount, is rejected whole, never
  partially applied); SC-8 (transmission confidentiality — the
  server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated plainly
  and not claimed here).

## Honesty: what is NOT in this build

The union spec ranks 26 functions across the 21 siblings; 13 are
implemented here. The following **Extended functions are specified
and ranked in `UNION-SPEC.md` but are NOT implemented** in this
build:

- AI, analytics & business intelligence (the reporting here is
  exact computed statements, not AI/BI analytics)
- Project, program & portfolio management (domain project
  accounting runs on top of a ledger substrate; this build is that
  substrate)
- Risk management & internal controls beyond the seed
  (separation of duties, approval-required posting, and the audit
  trail are that seed; there is no risk register or GRC module)
- Audit *management* workbenches (audit plans, workpapers,
  findings — the `audit` family's other half; this build carries
  the audit *trail*)
- Fixed assets, property & fleet management (an asset *account*
  in the chart is not an asset register or depreciation engine)
- Records, document management & retention beyond the audit trail
- Forecasting & enterprise performance management (EPM)
- Supply chain, warehouse & logistics
- Grants, federal aid & GovCon accounting specifics
- Cryptocurrency & blockchain investigation
- Time tracking & scheduling
- Electronic & digital signatures
- Payroll & labor
- Tax reporting & support
- Forensic accounting & financial investigation

Named scope limits inside the Core, stated plainly:

- **Payments are records, not rails:** the build records payments
  and applies them to invoices. It does not connect to card
  networks, purchase-card systems, or any payment gateway.
- **Expenses are records with approval:** there is no travel
  booking, per-diem engine, or reimbursement payment rail.
- **Period close locks the journal only:** creating or posting a
  journal entry dated in a closed period is rejected. Invoices,
  expenses, and budgets for a closed period are not locked in
  this build.
- **No sibling's description uses the words "general ledger" or
  "double-entry"** (verified by grep across all 21). The
  double-entry journal is the defining mechanism of the
  `accounting_core` claim family (8 siblings claiming accounting /
  financial management), included on that basis and stated here
  rather than attributed to a sibling's wording. Standalone
  accounts-payable / accounts-receivable modules were likewise
  not invented; invoicing and payments carry the claims that
  exist.

Further, plainly:

- **Encryption is a platform note, not a core function here:**
  the server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated
  plainly, and not claimed here.
- The demo identities (`alice`, `bob`, `carol`) are **hooks, not
  an identity provider**. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- This build is **not a FedRAMP authorization and not a CMMC
  certification**, and it does not claim either. The control
  mapping above states which baseline families the build's
  features answer to; nothing more.
