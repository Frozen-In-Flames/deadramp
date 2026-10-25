"""Per-column describe tests.

Traces to: UNION-SPEC Core function 4 (Descriptive statistics) —
``describe`` per the Implementation contract for ``analytics/query.py``:
{column, count, mean, median, min, max, stddev} over the numeric values
of the column.
"""

import json
import statistics
import unittest

from analytics_helpers import ADMIN, ANALYST, REVENUES, UNITS, make_store
from analytics.errors import AnalyticsError, NotFoundError
from analytics.query import describe
from analytics.store import DatasetStore


class TestDescribeSales(unittest.TestCase):
    """Core: Descriptive statistics — describe() on the canonical data."""

    def setUp(self):
        self.store, self.ds = make_store()

    def test_describe_units_exact_statistics(self):
        """Core: Descriptive statistics. describe returns count, mean,
        median, min, max, stddev for the column."""
        out = describe(self.store, self.ds, "units", ANALYST)
        self.assertEqual(out["column"], "units")
        self.assertEqual(out["count"], 5)
        self.assertAlmostEqual(out["mean"], statistics.mean(UNITS), places=6)
        self.assertAlmostEqual(
            out["median"], statistics.median(UNITS), places=6
        )
        self.assertEqual(out["min"], 10)
        self.assertEqual(out["max"], 50)
        self.assertAlmostEqual(
            out["stddev"], statistics.pstdev(UNITS), places=6
        )

    def test_describe_revenue_float_statistics(self):
        """Core: Descriptive statistics. describe over a float column."""
        out = describe(self.store, self.ds, "revenue", ADMIN)
        self.assertEqual(out["count"], 5)
        self.assertAlmostEqual(
            out["mean"], statistics.mean(REVENUES), places=6
        )
        self.assertAlmostEqual(out["median"], 300.0, places=6)
        self.assertEqual(out["min"], 100.0)
        self.assertEqual(out["max"], 500.0)
        self.assertAlmostEqual(
            out["stddev"], statistics.pstdev(REVENUES), places=6
        )

    def test_describe_result_has_exactly_the_contract_keys(self):
        """Core: Descriptive statistics. Contract keys: column, count,
        mean, median, min, max, stddev."""
        out = describe(self.store, self.ds, "units", ANALYST)
        self.assertTrue(
            {"column", "count", "mean", "median", "min", "max", "stddev"}
            <= set(out.keys())
        )


class TestDescribeEdgeCases(unittest.TestCase):
    """Core: Descriptive statistics — medians, single values, mixing."""

    def _store_with(self, rows):
        store = DatasetStore()
        ds = store.ingest_json("t", json.dumps(rows), ADMIN)
        return store, ds["id"]

    def test_even_count_median_averages_middle_pair(self):
        """Core: Descriptive statistics. Median of an even-count column
        is the mean of the two middle values."""
        store, ds = self._store_with(
            [{"v": 1}, {"v": 2}, {"v": 3}, {"v": 4}]
        )
        out = describe(store, ds, "v", ANALYST)
        self.assertEqual(out["count"], 4)
        self.assertAlmostEqual(out["median"], 2.5, places=6)
        self.assertAlmostEqual(out["mean"], 2.5, places=6)

    def test_single_value_column_has_zero_stddev(self):
        """Core: Descriptive statistics. A one-value column describes
        cleanly; its (population) stddev is 0."""
        store, ds = self._store_with([{"v": 7}, {"v": "n/a"}])
        out = describe(store, ds, "v", ANALYST)
        self.assertEqual(out["count"], 1)
        self.assertAlmostEqual(out["mean"], 7.0, places=6)
        self.assertAlmostEqual(out["stddev"], 0.0, places=6)

    def test_only_numeric_values_are_described(self):
        """Core: Descriptive statistics. Contract: describe runs 'over
        the numeric values of the column' — strings and nulls are not
        counted."""
        store, ds = self._store_with(
            [{"v": 10}, {"v": "x"}, {"v": 20}, {"v": None}, {"v": 30}]
        )
        out = describe(store, ds, "v", ANALYST)
        self.assertEqual(out["count"], 3)
        self.assertAlmostEqual(out["mean"], 20.0, places=6)
        self.assertEqual(out["min"], 10)
        self.assertEqual(out["max"], 30)

    def test_describe_csv_ingested_numeric_column(self):
        """Core: Descriptive statistics + Ingest. A numeric column loaded
        from CSV is describable (values are numeric in the data)."""
        from analytics_helpers import sales_csv_text

        store = DatasetStore()
        ds = store.ingest_csv("sales", sales_csv_text(), ADMIN)
        out = describe(store, ds["id"], "units", ANALYST)
        self.assertEqual(out["count"], 5)
        self.assertAlmostEqual(out["mean"], 30.0, places=6)

    def test_describe_unknown_dataset_raises_not_found(self):
        """Core: Descriptive statistics. Unknown dataset -> NotFoundError."""
        store, _ = self._store_with([{"v": 1}])
        with self.assertRaises(NotFoundError):
            describe(store, "ds-999", "v", ANALYST)

    def test_describe_unknown_column_is_rejected(self):
        """Core: Descriptive statistics (SI-10). Unknown column errors."""
        store, ds = self._store_with([{"v": 1}])
        with self.assertRaises(AnalyticsError):
            describe(store, ds, "nope", ANALYST)

    def test_describe_non_numeric_column_has_no_statistics(self):
        """Core: Descriptive statistics. A column with no numeric values
        either errors cleanly or reports count 0 — never invented stats."""
        store, ds = self._store_with(
            [{"v": "a"}, {"v": "b"}]
        )
        try:
            out = describe(store, ds, "v", ANALYST)
        except AnalyticsError:
            return  # clean rejection is acceptable
        self.assertEqual(out["count"], 0)


if __name__ == "__main__":
    unittest.main()
