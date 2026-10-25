"""Negative control: the suite must reject a mutant aggregation.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant aggregation (avg computed as sum, ignoring
the divisor) that the canonical expectation is shown to reject —
proving the suite catches that defect class rather than merely
passing.'

The mutant below computes avg as sum(values) with no division. Every
test asserts three things: the canonical expectation (statistics.mean),
that the implementation matches the canonical expectation, and that the
mutant value fails the canonical expectation — including a literal
assertRaises(AssertionError) demonstration that comparing the mutant
output against the canonical expectation is a test failure.
"""

import statistics
import unittest

from analytics_helpers import ANALYST, UNITS, make_store
from analytics.query import describe, run_query


def mutant_avg(values):
    """The defect under control: 'avg' that never divides."""
    return sum(values)


def mutant_grouped_avg(values):
    return sum(values)  # same defect, per-group flavour


class TestNegativeControlMutantAvg(unittest.TestCase):
    """Core: Descriptive statistics — negative control for avg-as-sum."""

    def setUp(self):
        self.store, self.ds = make_store()

    def test_canonical_avg_rejects_mutant(self):
        """Core: Descriptive statistics / negative control. avg(units)
        is 30.0; the mutant reports 150 and is rejected by the
        canonical expectation."""
        canonical = statistics.mean(UNITS)  # 30.0
        mutant = mutant_avg(UNITS)  # 150 — the defect
        self.assertNotEqual(mutant, canonical)
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant, canonical)

        result = run_query(
            self.store, self.ds,
            {"aggregates": [{"func": "avg", "column": "units",
                             "alias": "a"}]},
            ANALYST,
        )
        rows = result["rows"]
        actual = (rows[0]["a"] if isinstance(rows[0], dict)
                  else rows[0][result["columns"].index("a")])
        self.assertAlmostEqual(actual, canonical, places=6)
        self.assertNotEqual(actual, mutant)

    def test_canonical_describe_mean_rejects_mutant(self):
        """Core: Descriptive statistics / negative control. The same
        defect in describe()'s mean is likewise rejected."""
        canonical = statistics.mean(UNITS)
        mutant = mutant_avg(UNITS)
        out = describe(self.store, self.ds, "units", ANALYST)
        self.assertAlmostEqual(out["mean"], canonical, places=6)
        self.assertNotEqual(out["mean"], mutant)
        with self.assertRaises(AssertionError):
            self.assertAlmostEqual(mutant, out["mean"], places=6)

    def test_grouped_avg_rejects_mutant_with_group_divisor(self):
        """Core: Descriptive statistics / negative control. Grouped avg
        divides by the group size (widget n=3): canonical 80/3, mutant
        80 — rejected; and the gadget group (n=2) rejects its mutant
        too, so the divisor is proven group-local, not global."""
        result = run_query(
            self.store, self.ds,
            {
                "group_by": ["product"],
                "aggregates": [{"func": "avg", "column": "units",
                                "alias": "a"}],
            },
            ANALYST,
        )
        rows = result["rows"]
        dicts = (rows if rows and isinstance(rows[0], dict)
                 else [dict(zip(result["columns"], r)) for r in rows])
        by_product = {r["product"]: r["a"] for r in dicts}

        widget_values = [10, 20, 50]
        gadget_values = [30, 40]
        self.assertAlmostEqual(
            by_product["widget"], statistics.mean(widget_values), places=6
        )
        self.assertAlmostEqual(
            by_product["gadget"], statistics.mean(gadget_values), places=6
        )
        self.assertNotEqual(
            by_product["widget"], mutant_grouped_avg(widget_values)
        )
        self.assertNotEqual(
            by_product["gadget"], mutant_grouped_avg(gadget_values)
        )
        with self.assertRaises(AssertionError):
            self.assertAlmostEqual(
                mutant_grouped_avg(widget_values),
                by_product["widget"],
                places=6,
            )

    def test_mutant_is_rejected_for_a_second_dataset_size(self):
        """Core: Descriptive statistics / negative control. With n=4
        the mutant (sum=100) and the mean (25) diverge differently
        than with n=5, so a hard-coded 'divide by 5' defect would
        also be caught."""
        import json

        from analytics_helpers import ADMIN
        from analytics.store import DatasetStore

        store = DatasetStore()
        ds = store.ingest_json(
            "t", json.dumps([{"v": 10}, {"v": 20}, {"v": 30}, {"v": 40}]),
            ADMIN,
        )
        values = [10, 20, 30, 40]
        out = describe(store, ds["id"], "v", ANALYST)
        self.assertAlmostEqual(out["mean"], 25.0, places=6)
        self.assertNotEqual(out["mean"], mutant_avg(values))
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_avg(values), out["mean"])


if __name__ == "__main__":
    unittest.main()
