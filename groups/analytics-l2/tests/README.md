# Tests — Analytics L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/analytics-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 147 tests
PYTHONPATH=src python3 -m unittest discover -s tests -t .   # package mode, also green
```

Status at delivery: **136 tests, OK** against the implementation in
`../src/`. (The suite was first validated against an independent
reference implementation written from UNION-SPEC.md alone, then aligned
to the shipped implementation where the spec left a shape open — see
"Interpretation notes".) After the remainder additions below:
**147 tests, OK**.

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
| `test_additions.py` | Remainder addition (ADDENDUM.md) — spec integrity for the appended NetComm / Beacon sheet (membership, literal claim table, verbatim evidence, census citation, near-miss pins, group totals) + the fork's substrate case (customized dashboard composition; dashboard averages are means) |
| `analytics_helpers.py` | Canonical sales dataset + row-shape normalisation |

## Negative control

`test_negative_control.py` implements the contract's required mutant:
`avg` computed as `sum(values)`, ignoring the divisor. Each test asserts
the canonical expectation (`statistics.mean`), that the implementation
matches it, and — via a literal `assertRaises(AssertionError)` — that
the canonical expectation rejects the mutant output, for the whole
dataset (n=5), per-group (widget n=3, gadget n=2), and a second dataset
(n=4, so a hard-coded divisor is also caught).

Verified by mutation: patching `src/analytics/query.py` so both the
`avg` aggregate and `describe`'s mean return `sum(numbers)` makes the
suite fail with **12 failures**, including all 4 negative-control tests
(plus the describe, grouped-avg, aggregate, and service describe tests).

**Drill re-run for the remainder addition (unit
`addition:analytics-l2`).** The core is unchanged by the addition, so
the same drill was re-run in this tree: both avg sites patched to
return `sum(numbers)`, full suite ran — **147 tests, exactly 13
failures**: the shipped drill's 12 plus exactly 1 from the new
additions module (`test_additions.TestBeaconSubstrate.
test_dashboard_statistics_are_means_not_sums` — grouped avg 15 and
describe mean 20 asserted against the mutant's sums), tripping
exactly as designed. `query.py` was restored from the pre-mutation
copy (`scratch/query.py.premutation`) and verified SHA-256-identical
to the shipped hash
(`f15c9b8f528db4675de1437588aadf95a45067b0429bc1287a08ce6720faea2c`);
the suite re-ran green. Raw output: `scratch/additions_mutation_run.txt`.

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
