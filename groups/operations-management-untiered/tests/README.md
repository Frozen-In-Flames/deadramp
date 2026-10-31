# Tests — Operations Management, untiered set

## Run

```bash
cd groups/operations-management-untiered
PYTHONPATH=src python -m unittest discover -s tests
```

**127 tests, all green** (verified by the parent before shipping).

## Layout

The core test files are carried from the founding group
(`groups/operations-management-l2/tests/`) with the suite re-anchored
to this untiered set. The parent's `test_additions.py` is NOT carried:
it pins the founding group's remainder-census addition unit, which is
not this set's membership. `test_specs.py` is new, written for this
set. One labeling fix was made in the carry: the
`opsmgmt_helpers.py` docstring now names this untiered set instead of
the founding group; no test logic changed anywhere.

| File | Tests | Covers |
|---|---|---|
| `opsmgmt_helpers.py` | — | shared fixtures (store, audit log, demo users) |
| `test_access.py` | 11 | the 16-action RBAC matrix, role boundaries |
| `test_directory.py` | 12 | people/organizations, opaque references |
| `test_projects.py` | 9 | projects, membership, roles |
| `test_assets.py` | 9 | asset lifecycle and transitions |
| `test_work_orders.py` | 17 | work orders, assignment, overdue derivation |
| `test_inspections.py` | 9 | inspection immutability, verbatim outcomes |
| `test_usage.py` | 13 | integer-only quantities, immutability, reversals |
| `test_workflows.py` | 8 | workflow registry versioning, never-executes pin |
| `test_service.py` | 8 | HTTP service end-to-end, authn/authz, denied-attempt audit |
| `test_reports_search.py` | 10 | report counts, search across the substrate |
| `test_audit.py` | 10 | append-only audit, update/delete refusal, JSONL sink |
| `test_main_cli.py` | 1 | CLI entry point |
| `test_negative_control.py` | 2 | the `_is_overdue` subclass mutant (below) |
| `test_specs.py` | 8 | this set's spec sheets: exactly 20 sheets; membership == census unit `untiered:Operations Management`; tier discipline on every sheet (`cmmc_tier` null, impact "Unknown"); category on every sheet; every claim's evidence verbatim in its description (under the founding extractor's documented `\r`→space normalization); literal pins: 2 total claims, claims-by-fork (IVM SmartHub → `inspections_field_ops`; Boltline → `integrations`), and the 18-fork zero-claim set |

## Negative control

`test_negative_control.py` subclasses the store with a mutant whose
`_is_overdue` always returns `False` and asserts the canonical store
derives `overdue=True` for a past-due open work order where the mutant
does not — in both the single-record view and the list view. The
control exists so the derivation seam is proven load-bearing in this
tree, not merely present.

## Mutation-verification record

Drill run in this tree (raw output: `scratch/drill_output.txt`):

1. Saved the premutation copy (`scratch/store.py.premutation`) and
   SHA-256 of `src/opsmgmt/store.py`:
   `8fe67ec242573e5d001071174ea4853fee74995ccc0f3ce02fd1a25f0bc411a6`.
2. Replaced the body of `OpsStore._is_overdue` with `return False`.
3. Ran the full suite: **exactly 9 failures** —
   - `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_list_view_canonical_but_mutant_not`
   - `test_negative_control.TestNegativeControlMutantDerivation.test_overdue_work_order_overdue_canonical_but_mutant_not`
   - `test_reports_search.TestReport.test_report_overdue_is_now_dependent`
   - `test_reports_search.TestReport.test_report_shape_and_counts`
   - `test_service.TestFullFlow.test_full_flow`
   - `test_work_orders.TestOverdueDerivation.test_in_progress_past_due_overdue`
   - `test_work_orders.TestOverdueDerivation.test_now_forms`
   - `test_work_orders.TestOverdueDerivation.test_overdue_is_derived_not_stored`
   - `test_work_orders.TestOverdueDerivation.test_overdue_open_work_order_overdue`

   The same 9-test set as the founding group's own recorded drill —
   the carried suite detects the dead derivation identically at tier
   null.
4. Restored `store.py` from the premutation copy; SHA-256 verified
   identical to the premutation hash above (and to the founding
   group's shipped module). Full suite re-run: **127 tests, OK**.
