# Accounting L3-adjacent — merged build (Operation DeadRamp, Phase 2, Group 23)

This is the merged, clean-room implementation of the **Accounting
L3-adjacent** sibling group: **2 forks** from the FedRAMP Marketplace
that share the same function (Accounting) and the same trust tier
(CMMC L3-adjacent, equivalent to FedRAMP **High**), built as one
open-source service per the group's union spec,
[`UNION-SPEC.md`](UNION-SPEC.md).

## Lineage and reuse (read this first)

This build is a **cross-tier merge** under Operation DeadRamp's
Merge Rule. One parent is the shipped Group 5 build
([`../accounting-l2/`](../accounting-l2/)), itself the union of the
21 Accounting L2 (FedRAMP Moderate) forks. The other parent is this
group's 2 High forks. The merge takes the union of the baselines and
inherits the **highest tier in full** — so this tree is Group 5's
service, **uplifted to the FedRAMP High baseline**, extended by this
group's spec sheets.

Reuse is explicit: Group 5's code is our own (Apache-2.0). One
module is byte-identical to Group 5 (`__init__.py`); six are
modified for the uplift (`audit.py`, `access.py`, `store.py`,
`service.py`, `errors.py`, `__main__.py`). No vendor code, assets,
or branding from any sibling offering is used. Python 3, **standard
library only**, no external dependencies.

## The group, honestly

Neither of this group's two marketplace listings describes an
accounting system in its own prose. Trenchant Analytics' ACQBOT is
an AI-powered federal acquisition platform (2 tagged claims under
the group's verbatim taxonomy: AI/analytics, workflow); Citrix for
Government - High is a sovereign cloud / virtual-workspace enclave
(**zero tagged claims** — a zero-claim sheet, recorded in the spec,
not repaired). The 13 core functions below tag zero claims *in this
group*; they remain Core because the Merge Rule carries the L2 union
upward whole, and a wording artifact is not a downgrade. The full
reasoning, the near-misses, and the ranking are in
[`UNION-SPEC.md`](UNION-SPEC.md). All claim counts are a floor.

## The 13 core functions (at the High baseline)

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
   `paid`. Payments are records, not payment rails.
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
   ledger for it.
9. **Financial reporting** — computed from posted entries only:
   trial balance (per-account debit/credit columns, `balanced`
   computed from the rows), income statement for a period,
   balance sheet cumulative through a period (the `balanced` flag
   is computed, not asserted), and per-account balance and
   activity.
10. **Workflow & approvals** — the state machine shared by
    entries, invoices, and expenses (`draft → pending →`
    `posted` / `issued` / `approved`, plus `rejected` and `void`),
    with **separation of duties**: the approver or rejecter of an
    object is never its creator.
11. **API access** — every function above is exposed over a REST
    API (JSON), so the service composes with anything that speaks
    HTTP.
12. **Access control** — role-based access hooks: platform roles
    `admin`, `member`, `viewer`, plus **`auditor`** (audit review
    only) at this tier, with a permission matrix enforced on every
    operation, layered with book membership, and
    unsuccessful-logon lockout at the service layer.
13. **Audit log** — an append-only, **hash-chained,
    tamper-evident** audit trail: every book, membership, account,
    entry, invoice, payment, expense, budget, reconciliation, and
    period-close mutation, and every denied attempt, recorded with
    actor, action, target, and UTC timestamp — plus chain
    verification and audit query/reduction at this tier. Optional
    JSONL file persistence.

**Money is integer cents, everywhere.** Every amount field is
`*_cents` and must be an integer — booleans and floats are rejected
at the boundary, even integral floats — so all arithmetic is exact
by construction. Malformed input is rejected with a validation
error and leaves the store completely unchanged (no partial
application, no id consumed). Ids are sequential per object type:
`book-`, `acct-`, `je-`, `inv-`, `pay-`, `exp-`, `bud-`, `rec-`.

## What the High baseline added (the uplifts)

- **Hash-chained audit (AU-9/AU-3)** — every audit entry carries
  `seq`, `prev_hash`, and a SHA-256 `hash` over its canonical JSON;
  `AuditLog.verify_chain()` recomputes the chain and localizes the
  first tampered entry; exposed as `GET /audit/verify`.
- **Fail-closed audit writes (AU-5)** — if an audit write fails,
  the operation does not proceed: the audit append rolls back, and
  the store rolls back the whole mutation (no object created, no
  id consumed, state exactly as before).
- **Audit query (AU-6/AU-7)** — `GET /audit` accepts `actor`,
  `action`, `target`, `since`, and `until` filter parameters.
- **Logon lockout (AC-7)** — per-username consecutive
  authentication-failure tracking; lockout at 3 failures (default)
  for 300 seconds (default); locked attempts return 403 and are
  audited as `auth:locked`; a success resets the counter.
- **Auditor role (AC-5)** — `dana` holds `audit_read` and nothing
  else, so audit review is a duty separable from administration.

## How to run

From this directory:

```sh
PYTHONPATH=src python -m accounting serve --host 127.0.0.1 --port 8000
```

Options: `--audit-log PATH` (JSONL audit persistence),
`--certfile FILE --keyfile FILE` to serve over TLS (standard library
`ssl`), and `--max-failed-logins N` / `--lockout-seconds S` for the
AC-7 lockout. A startup line is printed once the server is
listening.

## Demo users, roles, and permissions

The server ships four documented **demo identities**, supplied per
request with the `X-User` and `X-Role` headers. The role header must
match the registry exactly, or the request is rejected with 401 (an
unknown user is also 401).

| User    | Role    | Permissions |
|---------|---------|-------------|
| `alice` | admin   | read, create_book, enter, submit, approve, pay, close, manage_members, audit_read, admin |
| `bob`   | member  | read, create_book, enter, submit, approve, pay, close |
| `carol` | viewer  | read |
| `dana`  | auditor | audit_read |

A permitted role performing a forbidden action gets 403; validation
failures get 400; unknown objects get 404. Errors are always JSON
`{"error": "..."}` and no stack trace is ever returned to a client.

## API endpoints

As Group 5 — see [`../accounting-l2/README.md`](../accounting-l2/README.md)
for the full table — with these High-tier changes:

| Method | Path | Permission | Description |
|--------|------|-----------|-------------|
| GET | `/audit?actor=&action=&target=&since=&until=` | audit_read | `{"entries": [...]}` filtered by any given parameters **[L3]** |
| GET | `/audit/verify` | audit_read | `{"ok": bool, "entries": n, "first_bad_index": i\|null}` — hash-chain verification **[L3]** |

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**273 tests**: the 219 Group 5 tests inherited (four files adapted
for the uplift, listed in [`tests/README.md`](tests/README.md))
plus 54 new tests for the chain, audit query, fail-closed
rollback, lockout, and auditor role. Two negative controls, both
mutation-verified with the drills recorded in `tests/README.md`:
the balance-check mutant (patching the real check made the suite
fail, 4 failures; the file was restored and SHA-256 verified), and
audit tamper localized at the exact entry index by
`verify_chain()`.

## Honesty section

- **Specs**: 2/2 forks spec'd from their own public descriptions,
  using Group 5's taxonomy matcher verbatim; 2 claims total; one
  zero-claim sheet (Citrix), recorded, not repaired. Counts are a
  floor, never a ceiling.
- **Not built here** (specified in the union spec, registered as
  gaps for the final batch): the Extended families — AI/analytics
  & BI (this group's one claimed Extended family), project/program/
  portfolio management, risk register & GRC beyond the SoD/audit
  seed, audit-management workbenches, fixed-asset registers,
  records retention beyond the audit seed, forecasting & EPM,
  supply chain, GovCon/grants specifics, crypto investigation,
  time tracking, e-signature, payroll, tax support, forensic
  investigation. The two members' own domains (an LLM/RPA
  acquisition platform; a sovereign cloud / DaaS enclave) belong to
  their own categories' groups and are not built here either.
- **Baseline gaps at High, named, not implied closed**: MFA /
  authenticator management (IA-2(1)/(2), IA-5) — the demo
  identities are **hooks, not an IdP**; production identity and
  MFA-grade authentication are the embedding organization's.
  FIPS-validated cryptography (SC-13) — Python's standard library
  is not a validated module, not claimed. Encryption at rest
  (SC-28) — deployment layer; TLS only when a certificate is
  configured. Audit retention enforcement (AU-11) — not
  implemented. Session lock / termination (AC-11/AC-12) — the
  service authenticates per request and holds no sessions.
- **Payments are records, not rails**: no card networks, gateways,
  or money movement exist in this build.
- The control mapping in the union spec states which baseline
  families the build's features answer to. It is **not** a FedRAMP
  authorization and **not** a CMMC certification, and it claims
  neither.
