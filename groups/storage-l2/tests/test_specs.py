"""Spec integrity: specs/specs.json against the registry and the
remainder census.

Membership must be exactly the census unit's fork set
({F1304222071}), the fork's own recorded fields must match
forks.json, the taxonomy must be the 11 families defined from
this fork's own description, every claim's evidence sentence must
appear verbatim in the fork's description, the census citations
must verify, and the checked absences must hold at token level.
"""

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"F1304222071"}
EXPECTED_FAMILIES = {
    "message_archiving", "storage_management", "retention",
    "search_discovery", "supervision", "policy_enforcement",
    "retrieval_export", "mail_platform_integration",
    "directory_integration", "message_encryption",
    "customer_key_custody",
}
ABSENT_TOKENS = (
    "legal hold", "backup", "restore", "snapshot", "replicat",
    "disaster", "dedup", "compress", "tier", "lifecycle",
    "cold storage", "immutable", "worm", "write once", "audit",
    "fips", "at rest", "capacity", "quota", "malware", "journal",
    "migration", "ingest", "object storage", "bucket",
    "block storage", "volume", "file share",
)


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
        unit = units["new-singleton:Storage|L2"]
        self.assertIsNone(unit["extends_group"])
        self.assertEqual(set(unit["fork_ids"]), EXPECTED_FORKS)
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["F1304222071"]
        row = self.registry["F1304222071"]
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"], row["product"])
        self.assertEqual(sheet["vendor"], "Proofpoint, Inc.")
        self.assertEqual(sheet["product"], "Proofpoint Email Archive")
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"], "Storage")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claims_match_the_taxonomy(self):
        sheet = self.sheets["F1304222071"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_FAMILIES)
        self.assertEqual(len(sheet["functions_claimed"]), 11)

    def test_evidence_is_verbatim(self):
        sheet = self.sheets["F1304222071"]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"],
                          claim["function_id"])

    def test_census_citations_verify(self):
        check = json.loads(
            (ROOT / "scratch" / "citation_check.json").read_text(
                encoding="utf-8"))
        results = check["F1304222071"]
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["verbatim_in_description"] for r in results))

    def test_checked_absences_hold(self):
        description = self.sheets["F1304222071"]["description"].lower()
        for token in ABSENT_TOKENS:
            self.assertNotIn(token, description, token)
        # the single "version" token names the premise equipment's
        # hardware variant, not content versioning
        self.assertEqual(description.count("version"), 1)
        self.assertIn("hardware-based version", description)


if __name__ == "__main__":
    unittest.main()
