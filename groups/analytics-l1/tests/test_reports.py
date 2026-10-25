"""Reporting & export tests.

Traces to: UNION-SPEC Core functions 6 (Reporting) and 7 (Export) /
ranking rows 2 (Reporting, 37 siblings) and 22 (Data export,
5 siblings); Implementation contract for ``analytics/reports.py``:
result_to_csv(result), result_to_json(result), report_html(title,
sections) with sections {heading, table, chart_svg}.
"""

import csv
import io
import json
import unittest

from analytics_helpers import ANALYST, make_store, result_dicts
from analytics.charts import chart_svg
from analytics.query import run_query
from analytics.reports import report_html, result_to_csv, result_to_json


class ReportBase(unittest.TestCase):
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
                "order_by": [{"column": "region", "direction": "asc"}],
            },
            ANALYST,
        )
        # rows: north/90, south/60


class TestExport(ReportBase):
    """Core: Export — datasets and query results out as CSV or JSON."""

    def test_result_to_csv_header_and_rows(self):
        """Core: Export. CSV export carries the result columns as the
        header and one line per row, in column order."""
        text = result_to_csv(self.result)
        parsed = list(csv.reader(io.StringIO(text)))
        self.assertEqual(parsed[0], self.result["columns"])
        self.assertEqual(len(parsed), 1 + 2)
        body = {row[0]: row for row in parsed[1:]}
        self.assertEqual(float(body["north"][1]), 90.0)
        self.assertEqual(float(body["south"][1]), 60.0)

    def test_result_to_csv_of_plain_query(self):
        """Core: Export. CSV export of an unaggregated result preserves
        every row."""
        plain = run_query(self.store, self.ds, {}, ANALYST)
        parsed = list(csv.reader(io.StringIO(result_to_csv(plain))))
        self.assertEqual(parsed[0], ["region", "product", "units",
                                     "revenue"])
        self.assertEqual(len(parsed), 1 + 5)

    def test_result_to_json_roundtrips_values(self):
        """Core: Export. JSON export parses back to the same values,
        with numbers still numeric."""
        payload = json.loads(result_to_json(self.result))
        if isinstance(payload, dict) and "rows" in payload:
            rows = result_dicts(payload)
            columns = payload["columns"]
        else:
            rows = payload
            columns = self.result["columns"]
        self.assertEqual(columns, ["region", "total"])
        by_region = {r["region"]: r["total"] for r in rows}
        self.assertEqual(by_region, {"north": 90, "south": 60})

    def test_result_to_json_is_valid_json_string(self):
        """Core: Export. result_to_json returns a JSON string."""
        text = result_to_json(self.result)
        self.assertIsInstance(text, str)
        json.loads(text)  # must not raise


class TestReportHtml(ReportBase):
    """Core: Reporting — an HTML report of titled sections."""

    def test_report_contains_title_headings_table_and_chart(self):
        """Core: Reporting. The bundle composes title, section heading,
        a table of the result, and the section's chart SVG verbatim."""
        svg = chart_svg(self.result, "region", "total", kind="bar",
                        title="Units")
        html = report_html(
            "Regional report",
            [{"heading": "Units by region", "table": self.result,
              "chart_svg": svg}],
        )
        self.assertIsInstance(html, str)
        self.assertTrue("<html" in html.lower()
                        or "<!doctype html" in html.lower())
        self.assertIn("Regional report", html)
        self.assertIn("Units by region", html)
        self.assertIn("north", html)
        self.assertIn("south", html)
        self.assertIn("90", html)
        self.assertIn(svg, html)

    def test_report_with_multiple_sections(self):
        """Core: Reporting. Every section renders, in order."""
        html = report_html(
            "Multi",
            [
                {"heading": "First section", "table": self.result,
                 "chart_svg": None},
                {"heading": "Second section", "table": None,
                 "chart_svg": None},
            ],
        )
        self.assertIn("First section", html)
        self.assertIn("Second section", html)
        self.assertLess(html.index("First section"),
                        html.index("Second section"))

    def test_report_section_with_neither_table_nor_chart(self):
        """Core: Reporting. A heading-only section renders without a
        table or chart and does not fail."""
        html = report_html(
            "Sparse",
            [{"heading": "Notes only", "table": None, "chart_svg": None}],
        )
        self.assertIn("Notes only", html)

    def test_report_section_with_chart_only(self):
        """Core: Reporting. A chart-only section embeds its SVG."""
        svg = chart_svg(self.result, "region", "total", kind="pie")
        html = report_html(
            "Charts",
            [{"heading": "Share", "table": None, "chart_svg": svg}],
        )
        self.assertIn(svg, html)

    def test_empty_report_renders_title(self):
        """Core: Reporting. A report with no sections still renders its
        title as a valid HTML string."""
        html = report_html("Empty report", [])
        self.assertIn("Empty report", html)
        self.assertTrue("<html" in html.lower()
                        or "<!doctype html" in html.lower())


if __name__ == "__main__":
    unittest.main()
