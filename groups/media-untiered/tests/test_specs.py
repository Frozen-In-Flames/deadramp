"""Spec integrity: specs/specs.json against the registry and the
remainder census.

Membership must be exactly the census unit's fork set
({FR2218359666}); the sheet must record tier null (cmmc_tier
None, fedramp_impact_level "Unknown" as in the source); the
taxonomy must be the 6 families defined from this fork's own
description; every claim's evidence sentence must appear in the
fork's description (whitespace-normalized — it carries a
paragraph break); the census citation must verify and serve as
the transport claim's evidence; and the checked absences must
hold at token level.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"FR2218359666"}
EXPECTED_FAMILIES = {
    "live_video_transport", "stream_encryption", "service_startup",
    "device_control", "stream_optimization", "status_monitoring",
}
ABSENT_TOKENS = (
    "record", "playback", "transcod", "library", "archive",
    "caption", "subtitle", "protocol", "schedul", "advertis",
    "analytics", "viewership", "drm", "rights management",
    "content delivery", "cdn", "storage", "audit",
    "access control", "authenticat", "single sign-on", "score",
    "scoring", "switch",
)


def load(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def ws(text):
    return re.sub(r"\s+", " ", text)


class SpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = {s["fork_id"]: s
                      for s in json.loads(
                          (ROOT / "specs" / "specs.json").read_text(
                              encoding="utf-8"))}
        cls.registry = {r["source_url"].rstrip("/").rsplit("/", 1)[-1]: r
                        for r in load("forks.json")}
        cls.census = load("remainder.json")

    def test_membership_is_exactly_the_census_unit(self):
        units = {u["unit_id"]: u for u in self.census["build_units"]}
        unit = units["untiered:Media"]
        self.assertEqual(unit["kind"], "untiered_set")
        self.assertIsNone(unit["tier"])
        self.assertEqual(set(unit["fork_ids"]), EXPECTED_FORKS)
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)

    def test_tier_discipline_on_the_sheet(self):
        sheet = self.sheets["FR2218359666"]
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["FR2218359666"]
        row = self.registry["FR2218359666"]
        self.assertEqual(sheet["vendor"], "Haivision Systems, Inc.")
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"],
                         "Haivision Hub for Government (HUB-GOV)")
        self.assertEqual(sheet["product"], row["product"])
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP In Process")
        self.assertEqual(sheet["authorization_status"],
                         row["authorization_status"])
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["deadramp_category"], "Media")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claims_match_the_taxonomy_exactly(self):
        sheet = self.sheets["FR2218359666"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_FAMILIES)
        self.assertEqual(len(sheet["functions_claimed"]), 6)

    def test_every_evidence_sentence_is_in_the_description(self):
        sheet = self.sheets["FR2218359666"]
        normalized = ws(sheet["description"])
        for claim in sheet["functions_claimed"]:
            self.assertIn(ws(claim["evidence"]), normalized,
                          claim["function_id"])

    def test_census_citation_verifies_and_is_transport_evidence(self):
        census_forks = {r["fork_id"]: r for r in self.census["forks"]}
        citations = census_forks["FR2218359666"]["citations"]
        self.assertEqual(len(citations), 1)
        sheet = self.sheets["FR2218359666"]
        self.assertIn(ws(citations[0]), ws(sheet["description"]))
        transport = [c for c in sheet["functions_claimed"]
                     if c["function_id"] == "live_video_transport"]
        self.assertEqual(len(transport), 1)
        self.assertEqual(ws(transport[0]["evidence"]), ws(citations[0]))

    def test_checked_absences_hold_at_token_level(self):
        low = self.sheets["FR2218359666"]["description"].lower()
        for token in ABSENT_TOKENS:
            self.assertNotIn(token, low, token)

    def test_on_demand_token_is_present_but_not_playback(self):
        """The absence discipline is honest in both directions:
        "on-demand" DOES occur in the description — describing
        the contribution network's availability, not stored-video
        playback — so playback is absent as a function while the
        token is not claimed absent."""
        low = self.sheets["FR2218359666"]["description"].lower()
        self.assertIn("on-demand low latency video contribution "
                      "network", low)
        self.assertNotIn("playback", low)

    def test_no_baseline_or_equivalence_language_in_sheet(self):
        sheet = self.sheets["FR2218359666"]
        self.assertNotIn("CMMC L", json.dumps(sheet))


if __name__ == "__main__":
    unittest.main()
