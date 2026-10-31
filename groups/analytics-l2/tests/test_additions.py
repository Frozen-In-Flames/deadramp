"""Remainder additions tests — unit ``addition:analytics-l2``.

Traces to: ADDENDUM.md (the 1 previously uncategorized fork spec'd
into this group: NetComm / Beacon, ``F1508127183``) and UNION-SPEC.md
Core functions 3/4/5/6 (Query, Descriptive statistics, Visualization,
Reporting). The spec-integrity tests pin the appended sheet
literally: membership against ``remainder.json``, the claim table,
verbatim evidence, the census citation, and the near-miss set. The
substrate case exercises the fork's one substantive claim family
(Visualization & dashboards, Core) the way the fork describes it —
a customized dashboard composed for an organization — and pins the
second claim's disposition (Sharing & collaboration, Extended).
"""

import json
import os
import unittest

from analytics_helpers import ADMIN, ANALYST, make_store, result_dicts
from analytics.charts import chart_svg
from analytics.query import describe, run_query
from analytics.reports import report_html
from analytics.store import DatasetStore

_GROUP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))
_SPECS = os.path.join(_GROUP_ROOT, "specs", "specs.json")
_UNION = os.path.join(_GROUP_ROOT, "UNION-SPEC.md")
_REMAINDER = os.path.join(_REPO_ROOT, "remainder.json")

FORK_ID = "F1508127183"
EXPECTED_CLAIMS = ["visualization", "collaboration"]
ALL_FAMILIES = [
    "ingest", "connectors", "storage", "query_search", "transform",
    "visualization", "reporting", "statistics_ml", "geospatial",
    "realtime", "alerts_monitoring", "export", "api", "collaboration",
    "governance", "access_control", "audit", "encryption", "archiving",
    "text_nlp", "media_analytics", "kpi", "bi_selfservice", "scheduling",
]


def _specs():
    with open(_SPECS) as fh:
        return json.load(fh)


def _sheet():
    return [s for s in _specs() if s["fork_id"] == FORK_ID][0]


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1/§2: the appended sheet, pinned literally."""

    def test_sheet_count_and_membership(self):
        """The group has 129 sheets; the appended sheet is exactly
        the census unit's fork, in last position."""
        specs = _specs()
        self.assertEqual(len(specs), 129)
        self.assertEqual(specs[-1]["fork_id"], FORK_ID)
        with open(_REMAINDER) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:analytics-l2"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])

    def test_sheet_metadata(self):
        """Vendor / product / tier / status as filed in the source."""
        sheet = _sheet()
        self.assertEqual(sheet["vendor"], "NetComm")
        self.assertEqual(sheet["product"], "Beacon")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Analytics")

    def test_literal_claim_table(self):
        """The fork claims exactly visualization + collaboration,
        in taxonomy order — no more, no fewer."""
        claimed = [c["function_id"] for c in _sheet()["functions_claimed"]]
        self.assertEqual(claimed, EXPECTED_CLAIMS)

    def test_zero_claim_families(self):
        """Every other taxonomy family is unclaimed by this fork."""
        claimed = {c["function_id"] for c in _sheet()["functions_claimed"]}
        self.assertEqual(set(ALL_FAMILIES) - claimed,
                         set(ALL_FAMILIES) - set(EXPECTED_CLAIMS))

    def test_evidence_is_verbatim_and_carries_the_match(self):
        """Each claim's evidence is drawn from the fork's own
        description (verbatim up to the extractor's 400-char
        truncation) and contains the token that fired the family:
        'customized dashboards' for visualization, 'online
        collaboration' for collaboration."""
        sheet = _sheet()
        desc = sheet["description"]
        tokens = {"visualization": "customized dashboards",
                  "collaboration": "online collaboration"}
        for claim in sheet["functions_claimed"]:
            ev = claim["evidence"]
            body = ev[:-3] if ev.endswith("...") else ev
            self.assertIn(body, desc)
            self.assertIn(tokens[claim["function_id"]], ev)

    def test_census_citation_verifies(self):
        """The census starting point is a verbatim substring of the
        fork's own cached description."""
        with open(_REMAINDER) as fh:
            rem = json.load(fh)
        entry = [f for f in rem["forks"] if f["fork_id"] == FORK_ID][0]
        self.assertEqual(len(entry["citations"]), 1)
        self.assertIn(entry["citations"][0], _sheet()["description"])

    def test_near_miss_pins(self):
        """Family-adjacent phrases are present in the description
        yet produced no claim — the taxonomy was not re-tuned:
        'analysis of complex data' is not statistics_ml; 'e-workflows'
        is not scheduling; 'security & privacy management' is not
        access_control; 'leverages the Amazon Web Services' is not
        connectors."""
        desc = _sheet()["description"]
        claimed = {c["function_id"] for c in _sheet()["functions_claimed"]}
        pins = [
            ("Improved access to and analysis of complex data", "statistics_ml"),
            ("e-workflows", "scheduling"),
            ("security & privacy management in the cloud", "access_control"),
            ("leverages the Amazon Web Services GovCloud", "connectors"),
            ("information management software solutions", "governance"),
        ]
        for phrase, family in pins:
            self.assertIn(phrase, desc)
            self.assertNotIn(family, claimed)

    def test_group_totals(self):
        """Combined group: 129 forks, 116 claiming, 422 claims;
        visualization 34, collaboration 22."""
        specs = _specs()
        self.assertEqual(len(specs), 129)
        self.assertEqual(sum(1 for s in specs if s["functions_claimed"]), 116)
        self.assertEqual(sum(len(s["functions_claimed"]) for s in specs), 422)
        counts = {}
        for s in specs:
            for c in s["functions_claimed"]:
                counts[c["function_id"]] = counts.get(c["function_id"], 0) + 1
        self.assertEqual(counts["visualization"], 34)
        self.assertEqual(counts["collaboration"], 22)

    def test_collaboration_disposition_is_extended(self):
        """UNION-SPEC stands Sharing & collaboration as Extended —
        the claim buys no core function (ADDENDUM §3)."""
        with open(_UNION) as fh:
            union = fh.read()
        row = [ln for ln in union.splitlines()
               if "Sharing & collaboration" in ln and "|" in ln]
        self.assertTrue(row and any("Extended" in ln for ln in row))


class TestBeaconSubstrate(unittest.TestCase):
    """ADDENDUM §2/§3: the fork's substantive surface run against
    the shipped core — a customized dashboard (Core 5/6) composed
    from an organization's own service data, with the descriptive
    statistics (Core 4) the toolset presupposes."""

    def _store(self):
        store = DatasetStore()
        text = json.dumps([
            {"service": "HR", "requests": 10},
            {"service": "HR", "requests": 20},
            {"service": "Finance", "requests": 30},
        ])
        ds = store.ingest_json("agency-services", text, ADMIN)
        return store, ds["id"]

    def test_customized_dashboard_composition(self):
        """Core 5/6: a per-organization dashboard = a grouped query
        rendered as a standalone SVG chart inside a titled HTML
        report bundle. No JavaScript, no external assets."""
        store, ds = self._store()
        result = run_query(store, ds, {
            "group_by": ["service"],
            "aggregates": [{"func": "sum", "column": "requests",
                            "alias": "total"}],
        }, ANALYST)
        rows = {r["service"]: r["total"] for r in result_dicts(result)}
        self.assertEqual(rows, {"HR": 30, "Finance": 30})
        svg = chart_svg(result, "service", "total", kind="bar",
                        title="Requests by service line")
        self.assertIn("<svg", svg)
        self.assertTrue(svg.strip().endswith("</svg>"))
        html = report_html("Agency services dashboard", [
            {"heading": "Requests by service line", "table": result,
             "chart_svg": svg},
        ])
        self.assertIn("Agency services dashboard", html)
        self.assertIn("Requests by service line", html)
        self.assertIn("<svg", html)

    def test_dashboard_statistics_are_means_not_sums(self):
        """Core 4: the averages behind the dashboard are means.
        Grouped avg over HR (10, 20) is 15; describe mean over
        (10, 20, 30) is 20. This is the additions case designed to
        trip under the group's avg-as-sum drill (ADDENDUM §6)."""
        store, ds = self._store()
        result = run_query(store, ds, {
            "group_by": ["service"],
            "aggregates": [{"func": "avg", "column": "requests",
                            "alias": "avg_requests"}],
        }, ANALYST)
        rows = {r["service"]: r["avg_requests"] for r in result_dicts(result)}
        self.assertEqual(rows["HR"], 15)
        self.assertEqual(rows["Finance"], 30)
        stats = describe(store, ds, "requests", ANALYST)
        self.assertEqual(stats["count"], 3)
        self.assertEqual(stats["mean"], 20)


if __name__ == "__main__":
    unittest.main()
