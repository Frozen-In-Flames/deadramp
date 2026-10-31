"""Remainder addition tests — unit addition:analytics-l1.

Traces to: ADDENDUM.md (the HP WXP Collaboration addition to the
Group 7 union). Two halves:

1. Spec integrity: the appended sheet for FR2017459185 is pinned
   literally — membership against remainder.json, the claim table
   under the group's verbatim 24-family taxonomy, verbatim evidence,
   the census citation, the near-miss families that must NOT be
   claimed, the two wording artifacts, and the group's combined
   totals (17 sheets, 57 claims).
2. Substrate: the addition fork is exercised against the shipped
   core in its own shape — collaboration-telemetry aggregates
   (counts only, no session content) ingested, queried, described,
   charted, exported, and audited. The core is unchanged by the
   addition (all three claimed families are Extended at this
   tier), so this is the standard carried treatment.
"""

import json
import os
import statistics
import unittest

from analytics_helpers import ADMIN, ANALYST, VIEWER, result_dicts
from analytics.audit import AuditLog
from analytics.charts import chart_svg
from analytics.query import describe, run_query
from analytics.reports import result_to_csv
from analytics.store import DatasetStore

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

FORK_ID = "FR2017459185"

DESC_S1 = ("Workforce Experience Platform (WXP) Collaboration, formerly "
           "the Vyopta Platform, is now part of HP Inc\u2019s portfolio "
           "of technology solutions.")
DESC_S2 = ("WXP Collaboration provides monitoring and analytics for "
           "collaboration and unified communication technology.")
DESC_S3 = ("It\u2019s suite of applications delivers single-pane-of-glass, "
           "enterprise-wide visibility, and insights across multi-vendor "
           "collaboration environments to improve IT efficiency, increase "
           "end user productivity, and accelerate workplace transformation "
           "and technology migrations.")

EXPECTED_CLAIMS = {
    "transform": DESC_S3,
    "alerts_monitoring": DESC_S2,
    "collaboration": DESC_S1,
}

# Families whose substance is adjacent in the description but whose
# patterns do not fire — pinned so the absence is a checked fact,
# not an oversight (see ADDENDUM.md near-misses).
NEAR_MISS_FAMILIES = {
    "visualization",   # "single-pane-of-glass" / "visibility", no dashboard word
    "realtime",        # monitoring with no live / real-time wording
    "statistics_ml",   # "analytics" / "insights" wording only, no ML/AI/statistical token
    "connectors",      # multi-vendor environments, no integration phrasing
    "reporting",       # no "report" token anywhere
    "kpi",             # "productivity" is not performance-management wording
    "ingest", "storage", "query_search", "export", "api", "governance",
    "access_control", "audit", "encryption", "archiving", "geospatial",
    "text_nlp", "media_analytics", "bi_selfservice", "scheduling",
}

CENSUS_CITATION = DESC_S2

# UC telemetry aggregates in the fork's shape: counts per vendor
# environment. No session content, no user data — aggregates only.
WXP_CSV = (
    "vendor,meetings,minutes,issues\n"
    "vendor-a,120,30,3\n"
    "vendor-b,85,60,1\n"
    "vendor-c,140,90,5\n"
)
MINUTES = [30, 60, 90]


def _specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _addition_sheet():
    sheets = [s for s in _specs() if s["fork_id"] == FORK_ID]
    assert len(sheets) == 1
    return sheets[0]


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1/§2: the appended sheet, pinned literally."""

    def test_sheet_count_and_append_position(self):
        """17 sheets; the addition is the last sheet, after the 16
        originally shipped (append, never inserted or re-sorted)."""
        specs = _specs()
        self.assertEqual(len(specs), 17)
        self.assertEqual(specs[-1]["fork_id"], FORK_ID)
        self.assertNotIn(FORK_ID, [s["fork_id"] for s in specs[:-1]])

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork set."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = [u for u in rem["build_units"]
                if u.get("unit_id") == "addition:analytics-l1"]
        self.assertEqual(len(unit), 1)
        self.assertEqual(unit[0]["fork_ids"], [FORK_ID])
        self.assertEqual(_addition_sheet()["fork_id"], FORK_ID)

    def test_fork_identity_fields(self):
        """LI-SaaS at L1, Certified — the tier baseline is unchanged
        by the addition (LI-SaaS is the Low subset; union stays Low)."""
        sheet = _addition_sheet()
        self.assertEqual(sheet["vendor"], "HP Inc.")
        self.assertEqual(sheet["product"],
                         "Workforce Experience Platform Collaboration")
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Analytics")
        self.assertEqual(sheet["service_model"], ["SaaS"])

    def test_literal_claim_table(self):
        """Exactly three claims under the verbatim taxonomy, with
        the exact evidence sentences (taxonomy order preserved)."""
        sheet = _addition_sheet()
        got = {c["function_id"]: c["evidence"]
               for c in sheet["functions_claimed"]}
        self.assertEqual(got, EXPECTED_CLAIMS)
        self.assertEqual(
            [c["function_id"] for c in sheet["functions_claimed"]],
            ["transform", "alerts_monitoring", "collaboration"])

    def test_evidence_is_verbatim_description_text(self):
        """Every claim's evidence is a verbatim substring of the
        fork's own description."""
        sheet = _addition_sheet()
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citation_verbatim_and_is_monitoring_evidence(self):
        """The census starting point was verified, not trusted: its
        one citation is verbatim in the description and is the
        alerts_monitoring claim's evidence sentence."""
        with open(os.path.join(_REPO_ROOT, "remainder", "class_all.json")) as fh:
            cls = json.load(fh)
        entry = [c for c in cls if c["fork_id"] == FORK_ID]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["citations"], [CENSUS_CITATION])
        sheet = _addition_sheet()
        self.assertIn(CENSUS_CITATION, sheet["description"])
        self.assertEqual(EXPECTED_CLAIMS["alerts_monitoring"], CENSUS_CITATION)

    def test_near_miss_families_not_claimed(self):
        """Adjacent substance that matches no pattern stays
        unclaimed — with the trigger phrases proven present in the
        description, so each absence is a checked fact."""
        sheet = _addition_sheet()
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertTrue(claimed.isdisjoint(NEAR_MISS_FAMILIES),
                        claimed & NEAR_MISS_FAMILIES)
        desc = sheet["description"]
        for phrase in ("single-pane-of-glass", "visibility", "multi-vendor",
                       "insights", "productivity", "unified communication"):
            self.assertIn(phrase, desc)
        self.assertNotIn("dashboard", desc.lower())
        self.assertNotIn("report", desc.lower())

    def test_wording_artifacts_pinned(self):
        """The two artifact-weight claims stand as recorded in
        ADDENDUM §2: the collaboration evidence is the product-name
        sentence, and the transform evidence is 'workplace
        transformation' (organizational change), not data wording."""
        self.assertIn("formerly the Vyopta Platform",
                      EXPECTED_CLAIMS["collaboration"])
        self.assertIn("workplace transformation",
                      EXPECTED_CLAIMS["transform"])
        # the transform evidence sentence contains no data wording
        # at all — the claim is the bare pattern on "transformation"
        self.assertNotIn("data", EXPECTED_CLAIMS["transform"])

    def test_group_totals_after_addition(self):
        """Combined union: 17 forks, 57 claims, 15 of 17 claiming;
        the three moved families stand at 4 / 4 / 2."""
        specs = _specs()
        total = sum(len(s["functions_claimed"]) for s in specs)
        self.assertEqual(total, 57)
        claiming = sum(1 for s in specs if s["functions_claimed"])
        self.assertEqual(claiming, 15)
        counts = {}
        for s in specs:
            for c in s["functions_claimed"]:
                counts[c["function_id"]] = counts.get(c["function_id"], 0) + 1
        self.assertEqual(counts["alerts_monitoring"], 4)
        self.assertEqual(counts["collaboration"], 4)
        self.assertEqual(counts["transform"], 2)


class TestAdditionSubstrate(unittest.TestCase):
    """ADDENDUM §3: the fork exercised against the unchanged core —
    UC telemetry aggregates in, analytics out, everything audited."""

    def setUp(self):
        self.audit = AuditLog()
        self.store = DatasetStore(audit=self.audit)
        self.dataset = self.store.ingest_csv("wxp-telemetry", WXP_CSV, ANALYST)
        self.ds = self.dataset["id"]

    def test_ingest_records_metadata_only(self):
        """Core 2 (Storage): the dataset record is the registry
        shape — metadata and provenance, no telemetry payload."""
        self.assertEqual(
            set(self.dataset.keys()),
            {"id", "name", "columns", "row_count", "created_by", "created_utc"})
        self.assertEqual(self.dataset["row_count"], 3)
        self.assertEqual(self.dataset["columns"],
                         ["vendor", "meetings", "minutes", "issues"])

    def test_grouped_query_and_describe(self):
        """Core 3/4: per-vendor meeting totals by grouped query,
        and describe over the minutes column with the exact mean —
        the assertion the group's avg-mutant drill trips on."""
        result = run_query(self.store, self.ds, {
            "group_by": ["vendor"],
            "aggregates": [{"func": "sum", "column": "meetings",
                            "alias": "total_meetings"}],
            "order_by": [{"column": "vendor", "direction": "asc"}],
        }, VIEWER)
        rows = result_dicts(result)
        self.assertEqual(
            [(r["vendor"], float(r["total_meetings"])) for r in rows],
            [("vendor-a", 120.0), ("vendor-b", 85.0), ("vendor-c", 140.0)])
        out = describe(self.store, self.ds, "minutes", VIEWER)
        self.assertEqual(out["count"], 3)
        self.assertAlmostEqual(out["mean"], statistics.mean(MINUTES), places=6)
        self.assertAlmostEqual(out["median"], 60.0, places=6)
        self.assertEqual(out["min"], 30)
        self.assertEqual(out["max"], 90)

    def test_chart_and_export(self):
        """Core 5/7: a standalone SVG chart (no script) and a CSV
        export from the same query result."""
        result = run_query(self.store, self.ds, {
            "select": ["vendor", "meetings"],
            "order_by": [{"column": "vendor", "direction": "asc"}],
        }, ANALYST)
        svg = chart_svg(result, "vendor", "meetings", kind="bar",
                        title="Meetings by vendor")
        self.assertTrue(svg.lstrip().startswith("<svg"))
        self.assertNotIn("<script", svg)
        csv_text = result_to_csv(result)
        self.assertIn("vendor-a", csv_text)
        self.assertIn("vendor-c", csv_text)

    def test_operations_are_audited(self):
        """Core 10 (Audit): ingest, query, and describe by the demo
        identities are all in the append-only trail."""
        run_query(self.store, self.ds, {"select": ["vendor"]}, VIEWER)
        describe(self.store, self.ds, "issues", ADMIN)
        entries = self.audit.entries()
        actions = {(e["actor"], e["action"]) for e in entries}
        self.assertIn(("bob", "ingest"), actions)
        self.assertIn(("carol", "query"), actions)
        self.assertIn(("alice", "describe"), actions)
        for e in entries:
            self.assertEqual(set(e.keys()),
                             {"ts", "actor", "action", "target", "details"})


if __name__ == "__main__":
    unittest.main()
