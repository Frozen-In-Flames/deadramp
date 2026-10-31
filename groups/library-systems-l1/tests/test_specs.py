"""Spec integrity: membership exactly the 2 no-signal forks, tier
fields as recorded, literal claim tables, claim evidence verbatim in
the cached descriptions, classification fields pinned against
remainder/nosignal_report.json (and classification sentences pinned
as NOT occurring in the cached descriptions)."""
import json, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]
EXPECTED = {
    "F1305132147": {"fedramp_impact_level": "LI-SaaS", "claims": {"platform_services", "integration"}},
    "FR1818459251": {"fedramp_impact_level": "Low", "claims": {"library_management", "integration", "library_automation", "accessibility"}},
}
FAMILIES = {"library_management","discovery_delivery","digital_preservation","course_resource_lists","research_activities","knowledge_management","platform_services","integration","library_automation","accessibility"}

def load(rel): return json.loads((REPO / rel).read_text(encoding="utf-8"))

class SpecTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = {s["fork_id"]: s for s in json.loads((ROOT/"specs"/"specs.json").read_text(encoding="utf-8"))}
        cls.uncovered = {r["fork_id"]: r for r in load("remainder/uncovered.json")}
        cls.report = {r["fork_id"]: r for r in load("remainder/nosignal_report.json")}
    def test_membership_exact(self):
        self.assertEqual(set(self.sheets), set(EXPECTED))
    def test_tier_fields_as_recorded(self):
        for fid, exp in EXPECTED.items():
            s = self.sheets[fid]
            self.assertEqual(s["fedramp_impact_level"], exp["fedramp_impact_level"])
            self.assertEqual(s["cmmc_tier"], "L1")
            self.assertEqual(s["authorization_status"], "FedRAMP Certified")
            self.assertEqual(s["service_model"], ["SaaS"])
            self.assertEqual(s["deadramp_category"], "Library Systems")
    def test_description_matches_cache(self):
        for fid in EXPECTED:
            self.assertEqual(self.sheets[fid]["description"], self.uncovered[fid]["description"])
    def test_claim_tables_literal(self):
        total = 0
        for fid, exp in EXPECTED.items():
            claimed = {c["function_id"] for c in self.sheets[fid]["functions_claimed"]}
            self.assertEqual(claimed, exp["claims"]); total += len(claimed)
            self.assertTrue(claimed <= FAMILIES)
        self.assertEqual(total, 6)
    def test_claim_evidence_verbatim_in_description(self):
        for s in self.sheets.values():
            for c in s["functions_claimed"]:
                self.assertIn(c["evidence"], s["description"], c["function_id"])
    def test_classification_fields_match_report(self):
        for fid in EXPECTED:
            s, r = self.sheets[fid], self.report[fid]
            self.assertEqual(s["classification_evidence"], r["evidence_sentence"])
            self.assertEqual(s["classification_source_url"], r["source_url"])
            self.assertEqual(r["category_proposal"], "Library Systems")
    def test_classification_sentence_not_in_description(self):
        for fid in EXPECTED:
            self.assertNotIn(self.sheets[fid]["classification_evidence"],
                             self.sheets[fid]["description"])
    def test_certified_services_never_a_claim_source(self):
        for s in self.sheets.values():
            self.assertNotIn("certified_services", json.dumps(s["functions_claimed"]))
if __name__ == "__main__": unittest.main()
