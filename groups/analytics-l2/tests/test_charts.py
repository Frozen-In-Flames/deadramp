"""Visualization tests.

Traces to: UNION-SPEC Core function 5 (Visualization) / ranking row 4
(Visualization & dashboards, 33 siblings); Implementation contract for
``analytics/charts.py``: chart_svg(result, label_column, value_column,
kind='bar'|'line'|'pie', title='') returns a standalone SVG string —
no JavaScript, no external assets.
"""

import unittest

from analytics_helpers import ANALYST, make_store
from analytics.charts import chart_svg
from analytics.errors import AnalyticsError
from analytics.query import run_query


class ChartBase(unittest.TestCase):
    def setUp(self):
        self.store, self.ds = make_store()
        self.result = run_query(
            self.store,
            self.ds,
            {
                "group_by": ["region"],
                "aggregates": [
                    {"func": "sum", "column": "units", "alias": "total"}
                ],
            },
            ANALYST,
        )


class TestChartSvg(ChartBase):
    """Core: Visualization — standalone SVG charts from query results."""

    def test_bar_chart_is_standalone_svg(self):
        """Core: Visualization. A bar chart is a complete SVG document
        string."""
        svg = chart_svg(self.result, "region", "total", kind="bar",
                        title="Units by region")
        self.assertIsInstance(svg, str)
        self.assertIn("<svg", svg)
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_bar_chart_has_bars_labels_and_title(self):
        """Core: Visualization. Bars are drawn for each row, category
        labels and the title appear as text."""
        svg = chart_svg(self.result, "region", "total", kind="bar",
                        title="Units by region")
        self.assertIn("<rect", svg)
        self.assertIn("north", svg)
        self.assertIn("south", svg)
        self.assertIn("Units by region", svg)

    def test_default_kind_is_bar(self):
        """Core: Visualization. Contract: kind defaults to 'bar'."""
        svg = chart_svg(self.result, "region", "total")
        self.assertIn("<svg", svg)
        self.assertIn("<rect", svg)

    def test_line_chart_renders_a_line(self):
        """Core: Visualization. kind='line' draws a connected line."""
        svg = chart_svg(self.result, "region", "total", kind="line",
                        title="Trend")
        self.assertIn("<svg", svg)
        self.assertTrue(
            any(tag in svg for tag in ("<polyline", "<path", "<line")),
            "line chart contains no line geometry",
        )
        self.assertIn("north", svg)

    def test_pie_chart_renders_slices(self):
        """Core: Visualization. kind='pie' draws slice geometry."""
        svg = chart_svg(self.result, "region", "total", kind="pie",
                        title="Share")
        self.assertIn("<svg", svg)
        self.assertTrue(
            "<path" in svg or "<circle" in svg,
            "pie chart contains no slice geometry",
        )
        self.assertIn("north", svg)
        self.assertIn("south", svg)

    def test_chart_contains_no_javascript_or_external_assets(self):
        """Core: Visualization. Contract: 'No JavaScript, no external
        assets' — for every chart kind."""
        for kind in ("bar", "line", "pie"):
            with self.subTest(kind=kind):
                svg = chart_svg(self.result, "region", "total", kind=kind)
                self.assertNotIn("<script", svg.lower())
                self.assertNotIn("<image", svg.lower())
                self.assertNotIn("href=", svg.lower().replace(
                    'href="http://www.w3.org/2000/svg"', ""))

    def test_chart_without_title_still_renders(self):
        """Core: Visualization. Title is optional (contract default '')."""
        svg = chart_svg(self.result, "region", "total", kind="bar")
        self.assertIn("<svg", svg)

    def test_invalid_kind_is_rejected(self):
        """Core: Visualization (SI-10). Kinds are exactly bar|line|pie."""
        with self.assertRaises((AnalyticsError, ValueError)):
            chart_svg(self.result, "region", "total", kind="radar")

    def test_unknown_label_column_is_rejected(self):
        """Core: Visualization (SI-10). The label column must exist in
        the result."""
        with self.assertRaises((AnalyticsError, ValueError, KeyError)):
            chart_svg(self.result, "nope", "total", kind="bar")

    def test_unknown_value_column_is_rejected(self):
        """Core: Visualization (SI-10). The value column must exist in
        the result."""
        with self.assertRaises((AnalyticsError, ValueError, KeyError)):
            chart_svg(self.result, "region", "nope", kind="bar")


if __name__ == "__main__":
    unittest.main()
