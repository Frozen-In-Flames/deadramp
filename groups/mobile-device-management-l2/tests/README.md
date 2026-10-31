# Tests — Mobile Device Management (MDM) L2 merged build (CMMC L2 / FedRAMP Moderate)

Stdlib `unittest` only. Every test module's header names the core
function / control family it traces to, per `../UNION-SPEC.md`.

## Run

```bash
cd groups/mobile-device-management-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 75 tests
```

Status at delivery: **75 tests, OK**.

## Layout

| File | Tests | Covers |
|---|---:|---|
| `test_access.py` | 7 | 13 Access control — exact permission matrix, `require()`; audit_read admin-only |
| `test_organizations.py` | 7 | 1 Organizations — record shape, duplicate refs, membership boundary, member management, read-only viewer |
| `test_inventory.py` | 4 | 2 Inventory — pinned record shape (no device-identifier field), per-org ref uniqueness, kind/money validation, filters |
| `test_orders.py` | 9 | 3 Service orders — type/target validation, AC-5 requester/decider separation, lifecycle states, fulfillment as the only provisioning-state mover |
| `test_workflows.py` | 3 | 4 Workflow registry — definition validation; the registry never executes (behavior pin + no execution entry point) |
| `test_contracts_quotes.py` | 4 | 5 Contracts & quotes — window validation, per-org ref uniqueness, cross-org references rejected |
| `test_bills_validation.py` | 6 | 6 Bills & validation — `YYYY-MM` period validation, expected-total rule (disconnected items excluded), variance arithmetic, runs modify nothing |
| `test_disputes.py` | 4 | 7 Disputes — the dispute cap (over-bill rejected whole, at-bill accepted), lifecycle, verbatim resolution |
| `test_budgets.py` | 6 | 8 Budgets — derived availability, stored record carries no derived keys, one budget per period, projections verbatim, money boundary |
| `test_chargebacks_alerts.py` | 4 | 9 Chargebacks, 10 Alerts — record validation, acknowledgement flow |
| `test_reporting.py` | 4 | 11 Search & summary — accessible-only results, counts/sums computed from records |
| `test_service.py` | 6 | 12 REST API — live HTTP: 401/403/404/400 semantics, the full order flow over HTTP, denied attempts audited with `:denied`, audit endpoint admin-only |
| `test_audit.py` | 4 | 14 Audit log — mutation recording, entry shape, JSONL persistence round-trip, no mutation API |
| `test_main_cli.py` | 1 | CLI — `python -m mdm serve` subprocess answers `/health` |
| `test_store_validation.py` | 3 | Cross-cutting SI-10 — failed operations consume no id, money boundary across entities, no score/rating/optimization field on any view |
| `test_negative_control.py` | 3 | Negative control (below) |
| `mdm_helpers.py` | — | Canonical fixture: organization by bob, erin added as staff member (the canonical decider), funded budget 1,000,000 − 300,000 − 200,000 = 500,000 available; outsider dave in no organization |

## Negative control

**`test_negative_control.py`** — the group's signature invariant
is **derived availability**: a budget's available value is
budget minus obligated minus spent, computed at read from the
obligation records, never stored. The mutant is an `MdmStore`
subclass (`MutantMdmStore`) whose `_available_cents` returns the
bare budget, ignoring obligations. The tests assert the canonical
expectation (availability is 500,000 on the funded fixture), that
the implementation matches it in both the budget view and the
organization summary, and — via a literal
`assertRaises(AssertionError)` — that the canonical expectation
rejects the mutant's outcome (the mutant reports the full
1,000,000 as available).

## Mutation verification

VERIFIED by the coordinator for this group: `_available_cents` in
the real `src/mdm/store.py` was patched to return the bare budget
and the suite was run against the patched implementation.

- Patched run: **75 ran, exactly 4 failed**:
  - `test_budgets.TestBudgets.test_availability_is_derived_at_read`
  - `test_negative_control.TestNegativeControlDerivedAvailability.test_canonical_expectation`
  - `test_negative_control.TestNegativeControlDerivedAvailability.test_implementation_matches_canonical_in_summary`
  - `test_reporting.TestSummary.test_summary_counts_and_sums`
- `store.py` was then restored from `scratch/store.py.premutation`
  and verified **SHA-256-identical** (`8c0c787a…`, recorded in
  `scratch/store.py.sha256`); the suite is green again (75/75).
  Raw drill output is in `scratch/mutation-run.txt`.

The failing set is exactly the derivation-dependent set: the
obligated/spent sums (computed separately in the budget view)
still pass under the mutant, the stored-record key pin is
untouched by this mutation, and the mutant's own subclass test
passes by construction, as expected.

## Interpretation notes

- Budget obligated/spent/available are derived at read: the
  tests pin this twice over, once through the public views and
  the summary, and once by asserting the raw stored budget
  record (`store._budgets`) carries exactly its eight stored
  keys and no derived key at all.
- An inventory item's provisioning state is event-driven, not
  date- or threshold-driven, so it *is* stored — and the order
  tests pin that fulfillment is the only transition that moves
  it (an approved-but-unfulfilled suspend leaves the item
  `active`). The distinction is deliberate and stated in the
  store's module docstring.
- Validation runs are event records of deterministic arithmetic
  over the registry at run time; a later inventory change does
  not rewrite an earlier run, and a run never modifies the bill
  (pinned by `test_validation_modifies_nothing`).
- The service test's user registry includes `erin` and `dave`
  beyond the CLI's three demo users, so membership and
  separation-of-duties flows can run over HTTP.
