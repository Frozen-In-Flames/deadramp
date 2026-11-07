# Final GAPS batch — Remainder Addition — Finance L2 (+4 forks)

This note records the second GAPS-batch unit in this group
directory: the closure of the 6 open entries of the GAPS.md
section "Remainder Addition — Finance L2 (+4 forks)" — the gap
entries `UNION-ADDENDUM.md` §5 registered when the remainder
forks Apptio TBM, CGI Momentum, Coupa Spend Management for
Federal, and Innovest Trust & Wealth Management joined the
founding union. The first batch unit's note is `BATCH.md`
(idx 337–346); this unit covers idx 589–594 in
`../../gaps-batch/inventory.json`.

**No re-judgments.** The drafted dispositions held on close
reading of `UNION-ADDENDUM.md` §5: the 5 build-extension entries
land as in-substrate records extensions and the 1 stub-engine
entry lands as a labeled reference implementation. `DECISION.md`
qualification 1 was not needed.

## What was built

One new module, `src/finance/extensions_addition.py`, adding a
second wrapper class `FinanceExtensionsAddition` over the core
`FinanceStore`, following the first unit's conventions exactly:
core state read only through the core store's public API, no
operation writes core state, RBAC through `finance.access`
before any state change or id allocation, denied attempts
audited on the core audit log under this unit's own `exta_`
action prefix (distinct from the first unit's `ext_`), and
fail-closed creation (if the audit write fails, the record
insertion and its id roll back before the error propagates).
All 8 pre-existing modules under `src/finance/` — including the
first unit's `extensions.py` — are byte-identical.

Tests: `tests/test_gaps_batch_addition.py` (41 tests) pins the
new surface per entry, including exact record key sets (no field
can hold a real account identifier, a routing/IBAN/sort-code/
card number, or a credit score — pinned by exact-key recursive
scans across one record of every new kind), the integer-cents
boundary (a rejected amount consumes no id), access rules (a
viewer write is denied and audited `exta_*:denied`; an outsider
is denied everywhere; the platform admin reaches without
membership), cross-program invisibility, derived-never-stored
pins, and the stub labels. Full suite: 267 → 308 tests, all
passing.

Fresh negative control (recorded in `tests/README.md`): the
ledger derivation seam `_account_totals` in
`extensions_addition.py`. Mutating the real seam so the credit
side is added to the debit total — silently corrupting every
derived balance while leaving every stored record's shape
intact — produced exactly 4 failures in the full suite; the
canonical scenario's expected totals and balance, the canonical/
mutant divergence check, and both surface-level balance tests
caught it. The premutation copy and its SHA-256 live in the
group's `scratch/`; the restored module is SHA-256-identical to
the premutation copy and the suite is green after restoration.

## Per-entry disposition

### idx 589 — built (build-extension)

> Federal financial management system of record (Momentum)

`register_ledger_account` (glac-), `record_journal_entry`
(jrnl-), `get_ledger_account`, `list_ledger_accounts`,
`list_journal_entries`, `ledger_account_view`, `trial_balance`.
The general-ledger system of record lands as the records
surface its name reduces to: a chart of ledger accounts (opaque
caller refs, unique within the program, plus titles held as
data) and journal entry records (a debit side, a credit side, a
positive integer-cent amount, a period, a memo label; both
sides must be registered accounts of the program and must
differ). Balances are derived at read — per-account debit and
credit totals via the `_account_totals` seam, balance = debits
minus credits — and the trial balance derives balanced totals
over all entries, or one period's. Records carry
`authoritative_here: False`: the agency's authoritative system
of record is the external ERP; no lifecycle is executed and no
entry moves money.

### idx 590 — built (build-extension)

> Procurement lifecycle engine: supplier identification, sourcing, contracting, invoicing, supplier payment execution (Coupa; its payments recorded here, deliberately NOT enlarging the earned-wage payment-rails gap)

`register_supplier` (supp-), `create_requisition` (reqn-),
`record_requisition_decision` (rdec-),
`create_contract_record` (cntr-), `create_purchase_order`
(pord-), `record_invoice` (invc-),
`record_supplier_payment_report` (spay-), stage getters/lists,
and `procurement_summary`. One record kind per lifecycle stage:
supplier registrations (opaque refs; `vetted_here: False`),
requisitions with the decider's label stored verbatim as a
separate decision record (`decided_here: False`; the
requisition record is left byte-identical), contract records
with a recorded integer-cent ceiling that bounds the orders
recorded against them (an order exceeding the remaining
ceiling is rejected whole and stores nothing), purchase orders
(`placed_here: False`), invoices inheriting the order's
contract, supplier, and period (`issued_here: False`), and —
per the entry's own parenthetical and `ADDENDUM.md` §5 —
supplier payment reports recorded in THIS family, outcomes
stored verbatim as reported by the paying system
(`paid_here: False`), deliberately not enlarging the
earned-wage disbursement family. No supplier record shape has
a field that could hold a bank account identifier.

### idx 591 — built (build-extension)

> Spend analytics engine (Coupa)

`spend_analytics(program_id, period, actor)`. The analytics
engine lands as a view derived at read over the substrate's own
recorded spend — the same posture as Core 7 reporting and
Core 5 spend-vs-budget: core bookings (non-cancelled, by kind,
attributed by start month exactly as Core 5 attributes them),
core earned-wage disbursements (by disbursement month), and
this unit's purchase orders and invoices (by recorded period)
— as counts and integer-cent sums only. The view's key set is
pinned by test to contain no rate, trend, forecast, average, or
grand-total key: invoice amounts restate order amounts at a
later lifecycle stage, so a single total across lifecycle
stages would double-count, and none is computed.

### idx 592 — built (build-extension)

> Technology business management & cloud cost allocation / optimization (FinOps) engine (Apptio)

`record_cost_allocation` (allo-), `tag_cost_allocation`
(ctag-), `record_optimization_report` (fopt-), lists, and
`finops_summary`. Cost allocation and chargeback land as
allocation records (source label, target label, period,
nonnegative integer-cent amount as recorded) with tag records
bound to existing allocations; cloud cost optimization lands
as outcome reports whose labels — and any savings figure — are
stored verbatim as reported by the FinOps engine that actually
ran (`optimized_here: False`, `savings_computed_here: False`
throughout). The summary derives counts and recorded-cent
totals overall and by target label; the savings total is a sum
of reported figures, stated as such.

### idx 593 — built (build-extension)

> Trust accounting & wealth management platform, multi-currency (Innovest; the union's "trading & investment execution" named absence still stands: Innovest asserts wealth management, not trading)

`open_trust_account` (tacc-), `record_trust_transaction`
(ttxn-), `record_position_report` (tpos-),
`get_trust_account`, `list_trust_accounts`,
`list_trust_transactions`, `list_position_reports`,
`trust_account_view`, `trust_summary`. Trust accounts bind to
core participants (opaque refs only) with a caller
`account_ref` unique within the program and a `currency_label`
held as data — multi-currency means the currency is a label;
no conversion is ever computed (`converted_here: False`) and
the summary sums no money across currencies. Transactions are
contribution / distribution / fee / income / adjustment
records with positive integer-cent amounts; the account view
derives totals by kind and the recorded balance at read
(contributions + income + adjustments − distributions − fees)
by the substrate's own recorded arithmetic, and the stored
account record carries no balance. Position values are stored
verbatim as reported by the custodian (`valued_here: False`);
no wealth is managed here (`managed_here: False`). **The named
absence stands**: this surface has no order or execution
operation of any kind — pinned by test
(`create_trade_order` / `execute_trade` / `place_trade` /
`buy` / `sell` do not exist on the class) — because the entry
itself asserts wealth management, not trading.

### idx 594 — reference (stub-engine, as drafted)

> AI / ML document processing & image recognition (Coupa)

`record_document_processing_job` (djob-),
`record_document_processing_report` (dprt-), getters/lists, and
`document_processing_summary` — a labeled reference
implementation. Document processing and image recognition are
engines over document content, and this substrate holds no
document content: a job record names a document by an opaque
caller reference and a kind (`document_processing` /
`image_recognition`), and a report record stores the processing
system's outcome label verbatim. Every record carries
`reference_stub: True`, `processed_here: False`,
`recognized_here: False`, and `content_held: False`, and no
record shape has a field that could hold document content or
an image.

## Honesty notes

- Nothing in this unit runs an agency's financial system,
  sources or pays a supplier, places an order, issues an
  invoice, optimizes cloud spend, values or manages a holding,
  executes a trade or an investment, or processes a document —
  and the honesty label saying so is on the face of every
  record.
- Every figure in every derived view is a count or an
  integer-cent sum over recorded values, derived at read and
  never stored, and every stored outcome, decision, savings
  figure, and position value is verbatim as reported by the
  system that actually produced it.
