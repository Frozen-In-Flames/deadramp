"""Spec integrity: specs/specs.json against the registry and the
remainder census.

Membership must be exactly the census unit's fork set
({FR2304546222}), the fork's own recorded fields must match
forks.json, the taxonomy must be the 8 families defined from this
fork's own description, and every claim's evidence sentence must
appear verbatim in the fork's description. The business_matchmaking
evidence is pinned to sentence 5: sentence 1 names the customer's
need, sentence 5 asserts provision (extractor correction 1).
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"FR2304546222"}
EXPECTED_FAMILIES = {
    "event_preparation", "conference_management", "vendor_outreach",
    "event_formats", "webinars", "business_matchmaking",
    "networking_roundtables", "speaker_engagements",
}
MATCHMAKING_EVIDENCE = (
    "Be assured that our gathering functions let you provide both "
    "safe and interactive webinars, business matchmaking, networking "
    "roundtables and speakers engagements.")


def load(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


class SpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = {s["fork_id"]: s
                      for s in json.loads(
                          (ROOT / "specs" / "specs.json").read_text(
                              encoding="utf-8"))}
        cls.registry = {row_id: row for row_id, row in
                        ((r["source_url"].rstrip("/").rsplit("/", 1)[-1], r)
                         for r in load("forks.json"))}
        cls.census = load("remainder.json")

    def test_membership_is_exactly_the_census_unit(self):
        units = {u["unit_id"]: u for u in self.census["build_units"]}
        unit = units["new-singleton:Event Management|L1"]
        self.assertIsNone(unit["extends_group"])
        self.assertEqual(set(unit["fork_ids"]), EXPECTED_FORKS)
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["FR2304546222"]
        row = self.registry["FR2304546222"]
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"], row["product"])
        self.assertIn("My Business Matches", sheet["vendor"])
        self.assertIn("Matchmaking", sheet["product"])
        self.assertEqual(sheet["fedramp_impact_level"], "Low")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Event Management")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claims_match_the_taxonomy(self):
        sheet = self.sheets["FR2304546222"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_FAMILIES)
        self.assertEqual(len(sheet["functions_claimed"]), 8)

    def test_evidence_is_verbatim(self):
        sheet = self.sheets["FR2304546222"]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"],
                          claim["function_id"])

    def test_matchmaking_evidence_is_the_provision_sentence(self):
        sheet = self.sheets["FR2304546222"]
        claim = next(c for c in sheet["functions_claimed"]
                     if c["function_id"] == "business_matchmaking")
        self.assertEqual(claim["evidence"], MATCHMAKING_EVIDENCE)
        self.assertNotIn("definitive source", claim["evidence"])

    def test_census_citations_verify(self):
        check = json.loads(
            (ROOT / "scratch" / "citation_check.json").read_text(
                encoding="utf-8"))
        results = check["FR2304546222"]
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["verbatim_in_description"] for r in results))


if __name__ == "__main__":
    unittest.main()
