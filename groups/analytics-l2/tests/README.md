# Tests — Analytics L2 merged build

Stdlib `unittest` only. Every test docstring names the UNION-SPEC core
function / spec claim it traces to.

## Run

```bash
cd groups/analytics-l2
PYTHONPATH=src python3 -m unittest discover -s tests        # 136 tests
PYTHONPATH=src python3 -m unittest discover -s tests -t .   # package mode, also green
```

Status at delivery: **136 tests, OK** against the implementation in
`../src/`. (The suite was first validated against an independent
reference implementation written from UNION-SPEC.md alone, then aligned
to the shipped implementation where the spec left a shape open — see
"Interpretation notes".)

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

Verified by mutation: patching `src/analytics/query.py` so both the
`avg` aggregate and `describe`'s mean return `sum(numbers)` makes the
suite fail with **12 failures**, including all 4 negative-control tests
(plus the describe, grouped-avg, aggregate, and service describe tests).

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
