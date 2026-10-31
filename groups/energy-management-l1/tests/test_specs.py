"""Spec integrity: specs/specs.json against the registry and the
remainder census.

Membership must be exactly the census unit's fork set
({FR2014363920}), the fork's own recorded fields must match
forks.json, the taxonomy must be the 9 families defined from this
fork's own description, and every claim's evidence sentence must
appear verbatim in the fork's description.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"FR2014363920"}
EXPECTED_FAMILIES = {
    "reverse_auction", "provider_choice", "budgeting_consulting",
    "market_intelligence", "risk_management_consulting",
    "price_trigger_alerts", "contract_change_notifications",
    "market_update_notifications", "price_charts",
}


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
        unit = units["new-singleton:Energy Management|L1"]
        self.assertIsNone(unit["extends_group"])
        self.assertEqual(set(unit["fork_ids"]), EXPECTED_FORKS)
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["FR2014363920"]
        row = self.registry["FR2014363920"]
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"], row["product"])
        self.assertIn("Enel X", sheet["vendor"])
        self.assertIn("Exchange", sheet["product"])
        self.assertEqual(sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(sheet["cmmc_tier"], "L1")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Energy Management")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claims_match_the_taxonomy(self):
        sheet = self.sheets["FR2014363920"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_FAMILIES)
        self.assertEqual(len(sheet["functions_claimed"]), 9)

    def test_evidence_is_verbatim(self):
        sheet = self.sheets["FR2014363920"]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"],
                          claim["function_id"])

    def test_census_citations_verify(self):
        check = json.loads(
            (ROOT / "scratch" / "citation_check.json").read_text(
                encoding="utf-8"))
        results = check["FR2014363920"]
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["verbatim_in_description"] for r in results))


if __name__ == "__main__":
    unittest.main()
