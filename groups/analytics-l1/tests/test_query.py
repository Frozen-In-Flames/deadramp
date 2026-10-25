"""Query & descriptive-statistics tests.

Traces to: UNION-SPEC Core functions 3 (Query & search) and 4
(Descriptive statistics — core slice of ranking row 1, Statistical /
predictive / ML & AI analysis, 45 siblings); ranking row 12 (Query &
search, 16 siblings); Implementation contract for ``analytics/query.py``.
"""

import statistics
import unittest

from analytics_helpers import (
    ANALYST,
    REVENUES,
    UNITS,
    VIEWER,
    make_store,
    result_dicts,
    sorted_dicts,
)
from analytics.errors import AnalyticsError, NotFoundError
from analytics.query import run_query


class QueryBase(unittest.TestCase):
    def setUp(self):
        self.store, self.ds = make_store()
        self.actor = ANALYST

    def query(self, q, actor=None):
        return run_query(self.store, self.ds, q, actor or self.actor)


class TestPlainAndSelect(QueryBase):
    """Core: Query & search — projection over a dataset."""

    def test_empty_query_returns_all_rows_and_columns(self):
        """Core: Query. run_query result is {columns, rows, row_count}
        covering the whole dataset."""
        result = self.query({})
        self.assertEqual(result["columns"], ["region", "product", "units",
                                             "revenue"])
        self.assertEqual(result["row_count"], 5)
        self.assertEqual(len(result["rows"]), 5)

    def test_plain_query_returns_the_ingested_values(self):
        """Core: Query. Unfiltered rows carry the ingested values."""
        rows = sorted_dicts(result_dicts(self.query({})), "units")
        self.assertEqual([r["units"] for r in rows], UNITS)
        self.assertEqual([r["region"] for r in rows],
                         ["north", "south", "north", "south", "north"])

    def test_select_restricts_columns(self):
        """Core: Query. `select` performs column selection (contract)."""
        result = self.query({"select": ["region", "units"]})
        self.assertEqual(result["columns"], ["region", "units"])
        rows = result_dicts(result)
        self.assertTrue(all(set(r.keys()) == {"region", "units"}
                            for r in rows))
        self.assertEqual(sorted(r["units"] for r in rows), UNITS)

    def test_select_single_column(self):
        """Core: Query. Single-column selection."""
        result = self.query({"select": ["product"]})
        self.assertEqual(result["columns"], ["product"])
        self.assertEqual(
            sorted(r["product"] for r in result_dicts(result)),
            ["gadget", "gadget", "widget", "widget", "widget"],
        )

    def test_select_unknown_column_is_rejected(self):
        """Core: Query (SI-10). Selecting a non-existent column errors."""
        with self.assertRaises(AnalyticsError):
            self.query({"select": ["nope"]})


class TestWhereFilters(QueryBase):
    """Core: Query — the filter operators named in the contract."""

    def _units(self, where):
        rows = result_dicts(self.query({"where": [where]}))
        return sorted(r["units"] for r in rows)

    def test_where_eq_on_string(self):
        """Core: Query. Filter op `eq`."""
        self.assertEqual(
            self._units({"column": "region", "op": "eq", "value": "north"}),
            [10, 30, 50],
        )

    def test_where_ne(self):
        """Core: Query. Filter op `ne`."""
        self.assertEqual(
            self._units({"column": "region", "op": "ne", "value": "north"}),
            [20, 40],
        )

    def test_where_lt(self):
        """Core: Query. Filter op `lt` (numeric comparison)."""
        self.assertEqual(
            self._units({"column": "units", "op": "lt", "value": 30}),
            [10, 20],
        )

    def test_where_le(self):
        """Core: Query. Filter op `le`."""
        self.assertEqual(
            self._units({"column": "units", "op": "le", "value": 30}),
            [10, 20, 30],
        )

    def test_where_gt(self):
        """Core: Query. Filter op `gt`."""
        result = self.query(
            {"where": [{"column": "revenue", "op": "gt", "value": 300}]}
        )
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(
            sorted(r["units"] for r in result_dicts(result)), [40, 50]
        )

    def test_where_ge(self):
        """Core: Query. Filter op `ge`."""
        self.assertEqual(
            self._units({"column": "units", "op": "ge", "value": 30}),
            [30, 40, 50],
        )

    def test_where_in(self):
        """Core: Query. Filter op `in` takes a list of candidates."""
        self.assertEqual(
            self._units(
                {"column": "region", "op": "in", "value": ["south"]}
            ),
            [20, 40],
        )
        self.assertEqual(
            self._units(
                {"column": "units", "op": "in", "value": [10, 50, 999]}
            ),
            [10, 50],
        )

    def test_where_contains(self):
        """Core: Query. Filter op `contains` matches substrings."""
        self.assertEqual(
            self._units(
                {"column": "product", "op": "contains", "value": "widg"}
            ),
            [10, 20, 50],
        )

    def test_where_with_no_matches_returns_empty_result(self):
        """Core: Query. A filter matching nothing is an empty result,
        not an error, and keeps its columns."""
        result = self.query(
            {"where": [{"column": "region", "op": "eq", "value": "east"}]}
        )
        self.assertEqual(result["rows"], [])
        self.assertEqual(result["row_count"], 0)
        self.assertEqual(result["columns"], ["region", "product", "units",
                                             "revenue"])

    def test_where_unknown_column_is_rejected(self):
        """Core: Query (SI-10). Filtering on a non-existent column errors."""
        with self.assertRaises(AnalyticsError):
            self.query({"where": [{"column": "nope", "op": "eq", "value": 1}]})

    def test_where_unknown_operator_is_rejected(self):
        """Core: Query (SI-10). Operators are exactly the contract set."""
        with self.assertRaises(AnalyticsError):
            self.query(
                {"where": [{"column": "units", "op": "approx", "value": 1}]}
            )


class TestAggregates(QueryBase):
    """Core: Descriptive statistics — aggregations in queries."""

    def test_aggregate_without_group_by_single_row(self):
        """Core: Descriptive statistics. count/sum/avg/min/max over the
        whole dataset collapse to one row."""
        result = self.query({
            "aggregates": [
                {"func": "count", "column": "units", "alias": "n"},
                {"func": "sum", "column": "units", "alias": "total"},
                {"func": "avg", "column": "units", "alias": "mean_units"},
                {"func": "min", "column": "units", "alias": "lo"},
                {"func": "max", "column": "units", "alias": "hi"},
            ]
        })
        self.assertEqual(result["row_count"], 1)
        row = result_dicts(result)[0]
        self.assertEqual(row["n"], 5)
        self.assertEqual(row["total"], 150)
        self.assertAlmostEqual(row["mean_units"], 30.0, places=6)
        self.assertEqual(row["lo"], 10)
        self.assertEqual(row["hi"], 50)
        for alias in ("n", "total", "mean_units", "lo", "hi"):
            self.assertIn(alias, result["columns"])

    def test_sum_of_revenue(self):
        """Core: Descriptive statistics. `sum` over a float column."""
        result = self.query({
            "aggregates": [
                {"func": "sum", "column": "revenue", "alias": "rev"}
            ]
        })
        self.assertAlmostEqual(
            result_dicts(result)[0]["rev"], sum(REVENUES), places=6
        )

    def test_stddev_aggregate_is_population_stddev(self):
        """Core: Descriptive statistics. `stddev` describes the column as
        a whole (population standard deviation)."""
        result = self.query({
            "aggregates": [
                {"func": "stddev", "column": "units", "alias": "sd"}
            ]
        })
        self.assertAlmostEqual(
            result_dicts(result)[0]["sd"],
            statistics.pstdev(UNITS),
            places=6,
        )

    def test_unknown_aggregate_func_is_rejected(self):
        """Core: Descriptive statistics (SI-10). Funcs are exactly
        count|sum|avg|min|max|stddev."""
        with self.assertRaises(AnalyticsError):
            self.query({
                "aggregates": [
                    {"func": "median", "column": "units", "alias": "m"}
                ]
            })

    def test_group_by_with_sum_and_count(self):
        """Core: Query + Descriptive statistics. `group_by` partitions
        rows; aggregates are computed per group."""
        result = self.query({
            "group_by": ["region"],
            "aggregates": [
                {"func": "sum", "column": "units", "alias": "total"},
                {"func": "count", "column": "units", "alias": "n"},
            ],
        })
        self.assertEqual(result["row_count"], 2)
        self.assertIn("region", result["columns"])
        self.assertIn("total", result["columns"])
        by_region = {r["region"]: r for r in result_dicts(result)}
        self.assertEqual(by_region["north"]["total"], 90)
        self.assertEqual(by_region["north"]["n"], 3)
        self.assertEqual(by_region["south"]["total"], 60)
        self.assertEqual(by_region["south"]["n"], 2)

    def test_group_by_avg_differs_per_group(self):
        """Core: Descriptive statistics. Per-group `avg` divides by the
        group size, not the dataset size."""
        result = self.query({
            "group_by": ["product"],
            "aggregates": [
                {"func": "avg", "column": "units", "alias": "avg_units"}
            ],
        })
        by_product = {r["product"]: r for r in result_dicts(result)}
        self.assertAlmostEqual(
            by_product["widget"]["avg_units"], 80.0 / 3.0, places=6
        )
        self.assertAlmostEqual(
            by_product["gadget"]["avg_units"], 35.0, places=6
        )

    def test_group_by_min_max(self):
        """Core: Descriptive statistics. Per-group `min`/`max`."""
        result = self.query({
            "group_by": ["region"],
            "aggregates": [
                {"func": "min", "column": "revenue", "alias": "lo"},
                {"func": "max", "column": "revenue", "alias": "hi"},
            ],
        })
        by_region = {r["region"]: r for r in result_dicts(result)}
        self.assertEqual(by_region["north"]["lo"], 100.0)
        self.assertEqual(by_region["north"]["hi"], 500.0)
        self.assertEqual(by_region["south"]["lo"], 250.0)
        self.assertEqual(by_region["south"]["hi"], 450.0)

    def test_group_by_unknown_column_is_rejected(self):
        """Core: Query (SI-10). Grouping on a non-existent column errors."""
        with self.assertRaises(AnalyticsError):
            self.query({
                "group_by": ["nope"],
                "aggregates": [
                    {"func": "count", "column": "units", "alias": "n"}
                ],
            })


class TestOrderAndLimit(QueryBase):
    """Core: Query — ordering and limit."""

    def test_order_by_descending(self):
        """Core: Query. order_by {column, direction} descending."""
        result = self.query(
            {"order_by": [{"column": "units", "direction": "desc"}]}
        )
        self.assertEqual(
            [r["units"] for r in result_dicts(result)],
            [50, 40, 30, 20, 10],
        )

    def test_order_by_ascending(self):
        """Core: Query. order_by ascending."""
        result = self.query(
            {"order_by": [{"column": "units", "direction": "asc"}]}
        )
        self.assertEqual(
            [r["units"] for r in result_dicts(result)],
            [10, 20, 30, 40, 50],
        )

    def test_order_by_aggregate_alias(self):
        """Core: Query. Ordering a grouped result by an aggregate alias."""
        result = self.query({
            "group_by": ["region"],
            "aggregates": [
                {"func": "sum", "column": "units", "alias": "total"}
            ],
            "order_by": [{"column": "total", "direction": "desc"}],
        })
        rows = result_dicts(result)
        self.assertEqual([r["region"] for r in rows], ["north", "south"])
        self.assertEqual([r["total"] for r in rows], [90, 60])

    def test_limit_truncates_after_ordering(self):
        """Core: Query. `limit` applies to the ordered result."""
        result = self.query({
            "order_by": [{"column": "units", "direction": "desc"}],
            "limit": 2,
        })
        self.assertEqual(result["row_count"], 2)
        self.assertEqual(
            [r["units"] for r in result_dicts(result)], [50, 40]
        )

    def test_limit_larger_than_result_returns_everything(self):
        """Core: Query. An over-large limit is not an error."""
        result = self.query({"limit": 100})
        self.assertEqual(result["row_count"], 5)

    def test_combined_pipeline(self):
        """Core: Query. select + where + order_by + limit compose."""
        result = self.query({
            "select": ["region", "units"],
            "where": [{"column": "units", "op": "ge", "value": 20}],
            "order_by": [{"column": "units", "direction": "asc"}],
            "limit": 3,
        })
        self.assertEqual(result["columns"], ["region", "units"])
        self.assertEqual(
            [r["units"] for r in result_dicts(result)], [20, 30, 40]
        )


class TestCompoundQueries(QueryBase):
    """Core: Query — list-form where / group_by / order_by compose."""

    def test_where_multiple_conditions_are_anded(self):
        """Core: Query. `where` is a list of conditions; all must hold
        (region=north AND units>=30 keeps only units 30 and 50)."""
        result = self.query({
            "where": [
                {"column": "region", "op": "eq", "value": "north"},
                {"column": "units", "op": "ge", "value": 30},
            ]
        })
        self.assertEqual(
            sorted(r["units"] for r in result_dicts(result)), [30, 50]
        )

    def test_group_by_multiple_columns(self):
        """Core: Query. `group_by` is a list: grouping by region and
        product yields one row per combination."""
        result = self.query({
            "group_by": ["region", "product"],
            "aggregates": [
                {"func": "sum", "column": "units", "alias": "total"}
            ],
        })
        self.assertEqual(result["row_count"], 4)
        combos = {
            (r["region"], r["product"]): r["total"]
            for r in result_dicts(result)
        }
        self.assertEqual(
            combos,
            {
                ("north", "widget"): 60,
                ("north", "gadget"): 30,
                ("south", "widget"): 20,
                ("south", "gadget"): 40,
            },
        )

    def test_order_by_multiple_keys(self):
        """Core: Query. `order_by` is a list: later keys break ties of
        earlier keys (region asc, then units desc within region)."""
        result = self.query({
            "order_by": [
                {"column": "region", "direction": "asc"},
                {"column": "units", "direction": "desc"},
            ]
        })
        rows = result_dicts(result)
        self.assertEqual(
            [(r["region"], r["units"]) for r in rows],
            [("north", 50), ("north", 30), ("north", 10),
             ("south", 40), ("south", 20)],
        )


class TestQueryIntegrity(QueryBase):
    """Core: Query — permissions, existence, and store immutability."""

    def test_viewer_may_query(self):
        """Core: Query + Access control. Viewer holds the query
        permission."""
        result = self.query({}, actor=VIEWER)
        self.assertEqual(result["row_count"], 5)

    def test_query_unknown_dataset_raises_not_found(self):
        """Core: Query. Unknown dataset id raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            run_query(self.store, "ds-999", {}, self.actor)

    def test_query_does_not_mutate_the_store(self):
        """Core: Query/Storage. Filtering and ordering are reads: the
        stored dataset is unchanged afterwards."""
        self.query({
            "where": [{"column": "region", "op": "eq", "value": "north"}],
            "order_by": [{"column": "units", "direction": "desc"}],
            "limit": 1,
        })
        again = self.query({})
        self.assertEqual(again["row_count"], 5)
        self.assertEqual(
            sorted(r["units"] for r in result_dicts(again)), UNITS
        )


if __name__ == "__main__":
    unittest.main()
