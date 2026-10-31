# Tests — Analytics L1 (Group 7)

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

This suite is **reused in full from our own shipped Group 1
(Analytics L2) suite** (Operation DeadRamp, Apache-2.0) — the same
10 core platform functions apply at this tier, and the Group 1
implementation in `../src/` is functionally tier-neutral. The reuse
is explicit, per the Group 7 task. Baseline framing for **this**
group is the lightest tier: FedRAMP Low / LI-SaaS ⇔ NIST SP 800-53
Rev. 5 Low ⇔ CMMC L1 / FAR 52.204-21. Baseline claims for this
group are made in this group's `UNION-SPEC.md` / `README.md`
(coordinator-owned); no Moderate-baseline claims are inherited
from Group 1.

## Run

```bash
cd groups/analytics-l1
PYTHONPATH=src python3 -m unittest discover -s tests        # 136 tests
PYTHONPATH=src python3 -m unittest discover -s tests -t .   # package mode, also green
```

Status at delivery: **136 tests, OK** against the implementation in
`../src/`. (The suite was first validated by Group 1 against an
independent reference implementation written from UNION-SPEC.md
alone, then aligned to the shipped implementation where the spec
left a shape open — see "Interpretation notes".)

## Layout

| File | Covers (UNION-SPEC Core) |
|---|---|
| `test_access.py` | 9 Access control — exact permission matrix, `require()` |
| `test_audit.py` | 10 Audit log — entry keys, append-only, JSONL file + reopen |
| `test_store.py` | 1 Ingest, 2 Storage — registry, sequential `ds-N` ids, SI-10 atomic rejection |
| `test_query.py` | 3 Query & search — select, all 8 filter ops, grouping, ordering, limit, compound list forms |
| `test_describe.py` | 4 Descriptive statistics — exact mean/median/min/max/stddev, numeric-only rule |
| `test_charts.py` | 5 Visualization — bar/line/pie standalone SVG, no JS/external assets |
| `test_reports.py` | 6 Reporting, 7 Export — `report_html`, `result_to_csv`, `result_to_json` |
| `test_service.py` | 8 API access — live HTTP server: auth 401, permission 403, validation 400, missing 404, `{error}` envelope, denied attempts audited |
| `test_main_cli.py` | `python -m analytics serve` subprocess with demo users alice/bob/carol |
| `test_negative_control.py` | Negative control (below) |
| `analytics_helpers.py` | Canonical sales dataset + row-shape normalisation |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
`avg` computed as `sum(values)`, ignoring the divisor. Each test asserts
the canonical expectation (`statistics.mean`), that the implementation
matches it, and — via a literal `assertRaises(AssertionError)` — that
the canonical expectation rejects the mutant output, for the whole
dataset (n=5), per-group (widget n=3, gadget n=2), and a second dataset
(n=4, so a hard-coded divisor is also caught).

## Mutation verification

VERIFIED for Group 7 (2026-10-25), reproduced against this tree.
The `avg` aggregation in `src/analytics/query.py` was patched to
return the bare sum, ignoring the divisor — in both places an average
is computed: the `avg` branch of `_aggregate`
(`return (sum(numbers)) if numbers else None`) and `describe`'s mean
(`"mean": sum(numbers)`) — the exact live counterpart of the mutant
in `test_negative_control.py`. The full suite was run: **136 tests
ran, 12 failed**. The failures are:

- `test_negative_control` — all 4 tests:
  `test_canonical_avg_rejects_mutant`,
  `test_canonical_describe_mean_rejects_mutant`,
  `test_grouped_avg_rejects_mutant_with_group_divisor`,
  `test_mutant_is_rejected_for_a_second_dataset_size`
- `test_describe` — 5 tests:
  `test_describe_units_exact_statistics`,
  `test_describe_revenue_float_statistics`,
  `test_describe_csv_ingested_numeric_column`,
  `test_even_count_median_averages_middle_pair`,
  `test_only_numeric_values_are_described`
- `test_query` — 2 tests:
  `test_aggregate_without_group_by_single_row`,
  `test_group_by_avg_differs_per_group`
- `test_service` — 1 test: `test_describe_endpoint`

`query.py` was then restored from a pre-mutation copy kept at
`scratch/query.py.pristine` (SHA-256
`f15c9b8f528db4675de1437588aadf95a45067b0429bc1287a08ce6720faea2c`,
verified identical to the pre-mutation hash and to Group 1's
`query.py`; `diff` against the pristine copy is empty) and the
suite re-run: **136 tests, OK** (both in the standard discovery
mode above and in package mode with `-t .`). The full mutant-run
output is kept at `scratch/mutation-run.txt`. The suite catches
this defect class; the negative control is not decorative.

## Remainder addition — unit `addition:analytics-l1` (2026-10-31)

`test_additions.py` (13 tests) pins the appended spec sheet for
`FR2017459185` (HP Inc. / Workforce Experience Platform
Collaboration): sheet count and append position, membership against
`remainder.json`, the literal claim table under the verbatim
24-family taxonomy (**transform**, **alerts_monitoring**,
**collaboration** — the latter two artifact-weight claims pinned as
artifacts, see `../ADDENDUM.md` §2), verbatim evidence, the census
citation, the near-miss absence set, and the combined group totals
(17 sheets, 57 claims). Its substrate half exercises the fork
against the unchanged core in its own shape: UC telemetry
aggregates ingested (metadata-only registry shape), per-vendor
grouped totals, `describe` statistics, an SVG chart and CSV export
from one query result, and the audit trail across the operations.

**Suite: 136 → 149 tests, all passing.**

**Mutation drill, re-run in this tree for the addition** (the core
is unchanged, so the group's signature drill applies): the `avg`
aggregation in `src/analytics/query.py` was patched to return the
bare sum in both places an average is computed (the `_aggregate`
avg branch: `return (sum(numbers)) if numbers else None`;
`describe`'s mean: `"mean": sum(numbers),`) and the full suite ran:
**149 tests, 13 failures** — the original drill's 12
(`test_negative_control` ×4, `test_describe` ×5, `test_query` ×2,
`test_service` ×1, the same set recorded above) plus exactly 1 from
the new additions module,
`test_additions.TestAdditionSubstrate.test_grouped_query_and_describe`,
tripping on its `describe` mean assertion exactly as designed.
`query.py` was restored from the pre-mutation copy
(`scratch/query.py.premutation_additions`) and verified SHA-256
`f15c9b8f528db4675de1437588aadf95a45067b0429bc1287a08ce6720faea2c`
— identical to the shipped hash and to `scratch/query.py.pristine`
— and the suite re-ran green (149 tests, OK). The failure list is
kept at `scratch/additions_mutation_failures.txt`.

## Interpretation notes

Where UNION-SPEC's contract left a shape open, the suite follows the
shipped implementation's documented choices and stays tolerant of the
remaining freedom (e.g. row dicts vs row lists are normalised before
comparison; creation returns 200 or 201):

- `where`, `group_by`, `order_by` are **lists** (`query.py` docstring).
- `stddev` is the **population** standard deviation (describe docstring).
- CSV values are stored as strings; numeric behaviour comes from the
  query/describe layer's coercion — CSV-origin tests therefore compare
  through `float()`.
- `GET /datasets` returns `{"datasets": [...]}` and `GET /audit`
  returns `{"entries": [...]}`; bare lists are also accepted.
