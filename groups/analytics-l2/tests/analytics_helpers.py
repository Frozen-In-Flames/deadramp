"""Shared helpers for the Analytics L2 merged-build test suite.

Traces to: UNION-SPEC.md "Implementation contract" — the suite is runnable
with ``PYTHONPATH=src``; these helpers additionally put ``src/`` on the path
so the tests also run standalone, and they normalise the two row shapes the
contract permits a query result to carry (list of dicts, or list of row
lists aligned to ``result["columns"]``) so value assertions stay exact
without over-constraining an implementation detail the spec leaves open.
"""

import copy
import os
import sys

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_SRC_DIR = os.path.join(_GROUP_ROOT, "src")
if os.path.isdir(_SRC_DIR) and _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)
if _TESTS_DIR not in sys.path:
    sys.path.insert(0, _TESTS_DIR)

from analytics.access import User  # noqa: E402
from analytics.store import DatasetStore  # noqa: E402

ADMIN = User("alice", "admin")
ANALYST = User("bob", "analyst")
VIEWER = User("carol", "viewer")

USERS_REGISTRY = {"alice": "admin", "bob": "analyst", "carol": "viewer"}

# Canonical dataset used across the suite. Hand-checkable aggregates:
#   units   = 10, 20, 30, 40, 50          -> sum 150, mean 30, pstdev sqrt(200)
#   revenue = 100, 250, 300, 450, 500     -> sum 1600, mean 320, median 300
#   by region: north units sum 90 / n 3 ; south units sum 60 / n 2
#   by product: widget units sum 80 / n 3 (avg 26.666...) ; gadget 70 / n 2 (avg 35)
SALES_ROWS = [
    {"region": "north", "product": "widget", "units": 10, "revenue": 100.0},
    {"region": "south", "product": "widget", "units": 20, "revenue": 250.0},
    {"region": "north", "product": "gadget", "units": 30, "revenue": 300.0},
    {"region": "south", "product": "gadget", "units": 40, "revenue": 450.0},
    {"region": "north", "product": "widget", "units": 50, "revenue": 500.0},
]
SALES_COLUMNS = ["region", "product", "units", "revenue"]
UNITS = [row["units"] for row in SALES_ROWS]
REVENUES = [row["revenue"] for row in SALES_ROWS]


def sales_rows():
    return copy.deepcopy(SALES_ROWS)


def sales_json_text():
    import json

    return json.dumps(SALES_ROWS)


def sales_csv_text():
    lines = [",".join(SALES_COLUMNS)]
    for row in SALES_ROWS:
        lines.append(
            "{region},{product},{units},{revenue:g}".format(**row)
        )
    return "\n".join(lines) + "\n"


def make_store(audit=None):
    """Fresh store with the canonical sales dataset ingested by the admin."""
    store = DatasetStore(audit=audit)
    dataset = store.ingest_json("sales", sales_json_text(), ADMIN)
    return store, dataset["id"]


def as_dicts(rows, columns=None):
    """Normalise rows (dicts or sequences) to a list of dicts."""
    out = []
    for row in rows:
        if isinstance(row, dict):
            out.append(dict(row))
        else:
            if columns is None:
                raise AssertionError(
                    "sequence rows require the result columns to normalise"
                )
            out.append(dict(zip(columns, row)))
    return out


def result_dicts(result):
    """Normalise a query/export result dict to a list of row dicts."""
    return as_dicts(result["rows"], result.get("columns"))


def sorted_dicts(dicts, key):
    return sorted(dicts, key=lambda d: d[key])
