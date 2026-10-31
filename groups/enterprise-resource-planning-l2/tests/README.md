# Tests — Enterprise Resource Planning L2 singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**81 tests, all passing** (Python 3 standard library `unittest`
only). Each test module's header names the core function, spec
claim, or control family it traces to.

| Module | Covers |
|---|---|
| `test_access.py` | Role/permission matrix (AC family) |
| `test_registries.py` | Organization, application & access-configuration registries: ref uniqueness, label-only shapes, deactivate lifecycles (SI-10) |
| `test_ledger.py` | **The signature invariant**: the balanced-entry seam, refusal of unbalanced / two-sided / zero entries whole (no id consumed), integer-cents boundary (float/bool/string rejected), derived totals never stored |
| `test_procurement.py` | Purchase orders: derived totals never stored, lifecycle transitions, line validation (SI-10) |
| `test_expenses.py` | Expense reports: derived totals, terminal outcome lifecycle, person-record requirement |
| `test_people.py` | Person records: pinned identifier-free shape (recursive scan), time entries (whole minutes, real dates), absence ranges |
| `test_payroll.py` | Payroll run records: caller-recorded integer cents, no computed field on the shape |
| `test_assets.py` | Asset records (caller-stated criticality labels) & work orders: fork's own kind vocabulary, assign/complete lifecycle, org-ownership guard |
| `test_inventory.py` | Inventory records: integer quantities, recorded adjustments, never negative |
| `test_documents.py` | Document records: pinned metadata-only shape (recursive no-content scan) |
| `test_integrations.py` | Integration & workflow registries: records only; **no execution surface exists** (structural pin over the store's public operations) |
| `test_reporting.py` | Search (literal, metadata-only) & summary: counts only, recursive no-score key scan |
| `test_audit.py` | Append-only audit log; mutations recorded, refusals not; `audit_read` admin-only; JSONL persistence |
| `test_service.py` | REST API over real HTTP: full flow through the balance gate, unbalanced → 400, float → 400, auth failures (401/403), exactly 4 denied attempts audited |
| `test_main_cli.py` | CLI argument handling and demo-user wiring |
| `test_specs.py` | Spec integrity: membership == the resolved fork {FR1710033970} in the census no-signal set, recorded fields match `forks.json`, taxonomy == the 24 own-words families, evidence verbatim, classification citation matches `nosignal_report.json` and does NOT occur in the description, checked absences hold at token level |
| `test_negative_control.py` | The mutation-verified negative control (below) |

## Negative control — mutation-verified

The signature invariant is the balanced-entry rule: a
general-ledger entry is recorded only when the single seam
`_check_entry_balanced` in `src/erp/store.py` accepts its lines —
every line one-sided, total debits equal to total credits, total
positive. An oracle that passes whether or not an entry balances
is testing that code ran, not that balance is enforced — so the
invariant is verified two ways:

1. **In-tree mutant** (`test_negative_control.py`): the canonical
   balance expectation is asserted against a run where the seam
   is swapped for a mutant that accepts every entry. The test
   asserts the canonical check fails against the mutant, and a
   second arm asserts the unbalanced entry is refused on the real
   store.
2. **External drill** (performed on this tree, recorded in
   `scratch/mutation-run.txt`): the seam body in the real
   `src/erp/store.py` was patched to `return None`, the full
   suite re-run, and the file then restored.

**Drill result: exactly 7 tests did not pass out of 81 (7
failures, 0 errors):**

- `test_ledger.LedgerEntryTests.test_unbalanced_entry_is_refused_whole`
- `test_ledger.SeamTests.test_seam_refuses_a_zero_total`
- `test_ledger.SeamTests.test_seam_refuses_two_sided_and_zero_lines`
- `test_ledger.SeamTests.test_seam_refuses_unequal_totals`
- `test_negative_control.NegativeControlTests.test_canonical_check_passes_on_the_real_store`
- `test_negative_control.NegativeControlTests.test_unbalanced_entry_refused_on_the_real_store`
- `test_service.ServiceTests.test_full_flow_with_balance_gate`

Every other test still passed against the mutant — the mutant
changes only whether ledger entries must balance, nothing else,
which is the point: the seven are exactly the tests that pin the
invariant. The store was then restored from
`scratch/store.py.premutation` and verified **byte-identical by
SHA-256** (`scratch/store.py.sha256`), and the full suite re-ran
green: **81 tests, OK**.
