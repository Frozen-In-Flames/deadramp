# Accounting — untiered set (Operation DeadRamp, Phase 2, remainder)

The merged build for the **1 untiered fork** of Accounting —
census unit `untiered:Accounting` in `../../remainder.json`,
Untiered Set 22 under the remainder pipeline. **This is an untiered
set, and that means something specific:** the member's FedRAMP
impact level is **Unknown** in the source dataset. The source
publishes no baseline for this offering, so **tier stays null**: no
tier is assigned, no CMMC equivalence is drawn, and this build
asserts **no control baseline**. Per PIPELINE.md, untiered
offerings "build to their documented control claims; tier stays
null in the registry until the source publishes a baseline." The
union contract is [`UNION-SPEC.md`](UNION-SPEC.md); the per-fork
spec sheet is in [`specs/specs.json`](specs/specs.json), recording
`fedramp_impact_level: "Unknown"` and `cmmc_tier: null`, pinned by
tests.

The fork was spec'd under the category's existing 26-function
taxonomy **verbatim** (AST-parsed out of the founding group's
extractor, never re-tuned). Taxonomy-verbatim proof: the extractor
first reproduced the founding Accounting L2 group's original
shipped claim tables exactly — **21 of 21 forks, 123 of 123 claims,
deep-equal** against the sheets at the founding ship commit
(`789c38c`) — before tagging this set. Result here: **3 claims** on
the set's 1 fork — `access_control` and `audit` on one first-party
sentence, and `financial_reporting` at **artifact weight** (it
fires on "vulnerability-reporting processes", a
security-transparency phrase, not a financial reporting function;
recorded in `scratch/ARTIFACTS.md`, not hidden or repaired). The
fork is not a zero-claim fork, and the category's centre is its
loudest named absence: the description is built around "a single
immutable financial ledger" yet fires no `accounting_core` phrase
("financial ledger" is not "general ledger").

The build implements the category's **thirteen-function
substrate** — the money machinery every accounting sibling's
platform presupposes — carried **byte-identical** from the founding
Accounting L2 build (`../accounting-l2/src/accounting/`, 7 of 7
modules; SHA-256 accounting below). The substrate is
tier-independent records code: the founding source contains no tier
or baseline machinery, so there was nothing tier-shaped to strip.
Where the founding contract's text says "L2 baseline hooks" for
access control, read it here as **baseline-neutral hooks**: at tier
null they are substrate, claimed against no baseline.

## The 1 fork

| Fork | Vendor | Product | Claims |
|---|---|---|---:|
| FR2633734927 | Meterbox Inc. | Meterbox | 3 (1 at artifact weight) |

In `forks.json` the fork is filed under Accounting; its source
business categories are Accounting, Finance, and Customer Relations
Management (CRM), and the census assigned it to Accounting, its
first business function — the spec sheet records the assignment.
Its authorization status as recorded is Initial Implementation, and
its service models are SaaS and PaaS — record data, not claims.

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
   balance (total debits equal total credits, in exact integer
   cents) or it is rejected whole. Entries are drafted, submitted,
   and **approved by someone other than their creator** (separation
   of duties) before they post; only posted entries touch the
   ledger, the balances, and the reports. A posted entry is never
   edited or voided — the correction is a reversing entry.
4. **Invoicing & billing** — invoices with line items (description,
   quantity, unit price in cents); line amounts and the invoice
   total are computed by the build, never trusted from the caller.
   Invoices run the same approval machine and become `issued` on
   approval.
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
8. **Reconciliation & period close** — an account can be reconciled
   for a period: the build computes its book balance through the
   end of that period and records the difference against a stated
   expected balance. Closing a period locks the ledger for it: no
   entry dated in it can be created or posted afterward.
9. **Financial reporting** — computed from posted entries only:
   trial balance (per-account debit/credit columns that must total
   equal, `balanced` computed from the rows), income statement for
   a period, balance sheet cumulative through a period (with
   cumulative net income; the `balanced` flag is computed, not
   asserted), and per-account balance and activity.
10. **Workflow & approvals** — the state machine shared by entries,
    invoices, and expenses (`draft → pending →` `posted` /
    `issued` / `approved`, plus `rejected` and `void`), with
    separation of duties: the approver or rejecter of an object is
    never its creator.
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

Two of the thirteen functions are claim-supported by this set's
fork under the category's standing dispositions — access control
(by `access_control`, full weight) and the audit log (by `audit`,
read at the trail end). The other eleven are **carried, not
claimed** (see `UNION-SPEC.md` for the full accounting, including
why financial reporting's artifact-weight family hit supports
nothing). No function is claimed to be *attained* by the fork — the
build is the merged open implementation, not the fork's product.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m accounting serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence), and
`--certfile FILE --keyfile FILE` to serve over TLS (standard
library `ssl`). A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships three documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header
must match the registry exactly, or the request is rejected with
401 (an unknown user is also 401).

| User    | Role    | Permissions                                  |
|---------|---------|----------------------------------------------|
| `alice` | admin   | read, create_book, enter, submit, approve, pay, close, manage_members, audit_read, admin |
| `bob`   | member  | read, create_book, enter, submit, approve, pay, close |
| `carol` | viewer  | read                                         |

A permitted role performing a forbidden action gets 403;
validation failures get 400; unknown objects get 404. Errors are
always JSON `{"error": "..."}` and no stack trace is ever returned
to a client.

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
| POST | `/books/{id}/entries` | enter | Body `{"date", "memo"?, "lines"}` (enter) → 201 entry dict |
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
prefixes (see `UNION-SPEC.md` and the founding group's spec for
every dict shape).

## How to run tests

Tests live in `tests/` (standard library `unittest`) and are
maintained separately against the same contract in `UNION-SPEC.md`:

```sh
PYTHONPATH=src python -m unittest discover -s tests
```

**225 tests, OK** at delivery: the founding group's 219-test core
suite carried with the code, plus spec tests pinning this set
(exactly 1 sheet; membership exact against `remainder.json`; the
sheet's tier null / impact "Unknown"; every claim's evidence
verbatim in its description; exactly 3 claims on exactly the
families {financial_reporting, audit, access_control}, with the
zero-claim set empty). The category's signature balance-check
mutation drill was re-run in this tree — exactly 4 failures under
the mutant, the founding drill's identical failure set, store
restored and SHA-256 verified (see `tests/README.md`).

## Byte-identity accounting

`src/accounting/` is carried from the founding group
`../accounting-l2/src/accounting/` — **7 of 7 modules
byte-identical**, SHA-256 (identical in both trees):

| Module | SHA-256 |
|---|---|
| `__init__.py` | `c1b0e6f18f2dbc4df102d05dac7970a5503bf9ec5d9b3425c5b0633b763b3ef5` |
| `__main__.py` | `fab67c941689b05bbf2d284e2ff8b8751092d3f573d257051821dae56bf6f24f` |
| `access.py` | `711542d2538d6eb947dc172fbafb46551a0884d24c05328f395fee8fbe171c83` |
| `audit.py` | `e8a1e7d2e4848c268ccd923990081e7eebf5630a6259bc99a65456d3d9929b1e` |
| `errors.py` | `bb90f2a4c86e107b5a69ca8ea75d97fda29f3ded03683c47a8b000ac9bd6f409` |
| `service.py` | `79ee7de765262ee4f7c23fe7147ad2a3c5f7ce012a4d0ebe648e995513c980f6` |
| `store.py` | `fb7eff3d22b40f2f0885f7b02650f1a0bba3b4d346ff2493d3a1af67751c2274` |

The shipped tree contains exactly the package under
`src/accounting/` — nothing flat at the `src/` root. The test suite
is likewise carried (all twelve founding test modules), with one
labeling fix in `tests/accounting_helpers.py` (its docstring now
names this untiered set instead of L2) and the new
`tests/test_specs.py` added. Full accounting is in
`tests/README.md`.

## Documented control claims (no baseline asserted)

**Tier discipline, stated plainly:** the source publishes no
FedRAMP impact level for this offering (all "Unknown"), so this
build asserts **no FedRAMP baseline, no CMMC tier, and no
equivalence**. What follows is only what the fork's own marketplace
description asserts, in its own words, under the taxonomy families
that carry control language. A documented control claim is a
**fork's claim about itself**, recorded with its evidence in
`UNION-SPEC.md` and `specs/specs.json`; it is not the build's
control attainment, and nothing here fills a family in from any
baseline.

Documented by the set's fork:

- **Identification & authentication (IA)** and **Access control &
  least privilege (AC)** — via `access_control`: Meterbox —
  "strong authentication and access controls" (both the
  `authentication` and the `access control` alternatives of the
  family fire on the fork's own sentence; full weight).
- **Audit logging (AU)** — via `audit`: Meterbox — "comprehensive
  auditability", recorded at the audit-*trail* end of the family;
  no audit-management capability is documented by it.

Recorded at prose weight, converted to no family:

- **Privacy language** — "customer data isolation, privacy by
  default" and "support for privacy and data-rights requirements":
  asserted about the offering itself, but no Accounting taxonomy
  family traces privacy language, so it converts to no claim.

**Not documented** by the fork: every other NIST SP 800-53 control
family — including AT, CA, CM, CP, IR, MA, MP, PE, PL, PM, PS, RA,
SA, SC, and SI **as control claims** — is asserted by no sentence
in the description. Two bounds stated explicitly: **SC is not
documented** (the word "encrypt" occurs nowhere, despite "data
isolation" and "privacy by default"); **CA is not documented** (the
closing sentence's "being built toward major enterprise security
and compliance standards" is future-directed aspiration, not a
claim of current assessment or certification). If the source later
publishes an impact level for this offering, the tier is recorded
then and not before.

## Honesty: what is NOT in this build

- **Tier null, plainly.** This build claims no FedRAMP baseline,
  no CMMC tier, and no authorization — for the fork or for itself.
  The fork's recorded authorization status is source data, not a
  claim by this build, and the fork's documented control language
  is recorded as *its* claim, never as the build's control
  attainment.
- **The substrate is carried, mostly not claimed.** Eleven of the
  thirteen core functions have no claim support from this set's
  fork: its description tags no `accounting_core`,
  `invoicing_billing`, `payment_processing`,
  `reconciliation_close`, `budgeting_planning`,
  `workflow_approvals`, or `api_integration` phrase, and its one
  `financial_reporting` hit is the artifact-weight
  "vulnerability-reporting" hit, which documents no reporting
  capability. The functions are implemented because they are the
  category substrate every accounting platform presupposes — the
  founding group's design — not because this fork's prose claims
  them.
- **Extended functions are specified, not implemented.** The union
  spec ranks 26 functions; the substrate behind 13 is implemented
  here. The Extended function that gains a claimant from this set
  is audit *management* workbenches (audit plans, workpapers,
  findings — 1 claimant, whose claim is recorded at the trail end);
  the founding group's remaining extended tail (AI/analytics & BI,
  project/program/portfolio management, risk register & GRC beyond
  the seed, fixed-asset registers, records retention beyond the
  audit seed, forecasting & EPM, supply chain, GovCon/grants
  specifics, crypto investigation, time tracking, e-signature,
  payroll, tax support, forensic investigation) stands registered
  under the founding group in `UNION-SPEC.md`'s ranking and is not
  re-registered here.
- **Payments are records, not rails:** the build records payments
  and applies them to invoices. It does not connect to card
  networks, purchase-card systems, or any payment gateway.
- **Expenses are records with approval:** there is no travel
  booking, per-diem engine, or reimbursement payment rail.
- **Period close locks the journal only:** creating or posting a
  journal entry dated in a closed period is rejected. Invoices,
  expenses, and budgets for a closed period are not locked in this
  build.
- **Encryption is a platform note, not a core function here:** the
  server runs over TLS when a certificate is configured;
  encryption at rest is a deployment-layer control, stated plainly,
  and not claimed here — and the fork documents no encryption claim
  of its own (see above).
- **Demo identities are hooks, not an IdP.** `alice`, `bob`, and
  `carol` are documented demo identities supplied by header; the
  service enforces the role permission matrix on those hooks and
  ships no identity provider, no credential store, and no
  authentication of its own. Production identity, authentication
  strength, and account lifecycle belong to the embedding
  organization.
- **Named absences stand.** Core accounting has 0 claimants in
  this set (the ledger prose fires no family phrase); payment
  processing, reconciliation & close, APIs & integrations,
  invoicing & billing, records & retention, risk & internal
  controls, and workflow & approvals likewise stand at 0 of 1,
  several with substance present in other words. Nothing was
  back-filled to make the set look complete.
