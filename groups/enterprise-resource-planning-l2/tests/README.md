# Tests — Enterprise Resource Planning L2 singleton

Run from this directory:

```sh
PYTHONPATH=src python3 -m unittest discover -s tests
```

**81 tests at delivery, 118 tests after the final GAPS batch,
all passing** (Python 3 standard library `unittest` only). Each
test module's header names the core function, spec claim, or
control family it traces to.

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
| `test_gaps_batch.py` | Final GAPS batch: the extension surface in `../src/erp/extensions.py` — one class per open GAPS.md entry for this group, the stub labels, and the cross-cutting boundary pins (below) |

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

## Final GAPS batch (2026-11-07)

`test_gaps_batch.py` (37 tests) pins the extension surface in
`../src/erp/extensions.py` (`ErpExtensions`, a wrapper around
the core `ErpStore`; every core module is byte-identical to its
pre-batch state): one test class per open GAPS.md entry for
this group (see `../BATCH.md` for the per-entry disposition),
plus cross-cutting pins — viewer denials on extension
mutations, `ext_`-prefixed actions on the core audit log, and a
recursive forbidden-key scan (no score / rating / rank / grade /
email / phone / SSN / fraud field can exist on any extension
record or evaluation).

Per entry, the pins that carry the honesty of the disposition:
portal layouts are derived in position order while the stored
widget list keeps recording order; lake queries apply the
declared schema at read over the core's *current* records (a
record created after registration appears in the next query,
and the stored dataset holds no rows); close balances,
consolidation totals, settlement state, production completion,
exchange feeds, pipeline counts, schedule coverage / gaps /
double-bookings, payroll gross / deductions / net, dashboard
metrics, plan actuals / variance / forecast, and risk exposure
are all derived at read — the stored records' exact key sets
are pinned so no derived value can be hiding on them; payment
instructions are capped by the guard seam at the purchase
order's derived total and a refusal consumes no id; production
output lands on the core inventory record through the core's
own recorded adjustment and over-plan output is refused whole;
the scheduling view is labeled `deterministic_coverage` (no
optimization is performed or claimed); the four stub-engine
entries' records all carry `reference_stub: True` and status
`recorded_reference_only` (the federation records also carry
`hook_only: True`), the gateway stub refuses a route against a
non-gateway integration, and the expense-policy evaluation is
labeled `deterministic_limit_check` — its findings state
recorded limit breaches only, and the recursive scan pins that
no fraud determination exists anywhere in it.

### Batch negative control — mutation-verified

VERIFIED by the coordinator (2026-11-07). The signature guard
of the source-to-settle extension,
`_check_instruction_within_total` in `src/erp/extensions.py`,
was patched from `if instructed_cents + amount_cents >
total_cents:` to `if False:` — computing the totals but never
comparing them against the purchase order's derived total —
and the full suite was run: **118 tests ran, exactly 1 failed**
(`test_gaps_batch.TestSourceToSettle
.test_instruction_cap_guard_and_no_id_consumed_on_refusal`).
`extensions.py` was then restored from
`scratch/extensions.py.premutation` (SHA-256 verified identical
to the pre-mutation hash,
`8c781caec5c25cb5622eaeb40801e1226182472bc4f802a2c36e37b2f4a5df46`;
drill record in `scratch/gaps-mutation-run.txt`) and the suite
re-run: **118 tests, OK**.

Full suite status after the batch: **118 tests, OK** (81 at
delivery + 37 batch tests).
