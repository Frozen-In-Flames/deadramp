"""Spec integrity: specs/specs.json against the registry, the
remainder census, and the no-signal resolution.

Membership must be exactly the one fork this build specs
(FR1710033970); the fork's own recorded fields must match
forks.json; the taxonomy must be the 24 families defined from
this fork's own description (plus its classification sentence for
the suite family); every claim's evidence sentence must appear
verbatim in the fork's description; the classification citation
must match remainder/nosignal_report.json exactly and must NOT
occur in the description (the two evidence streams never mix);
and the checked absences must hold at token level.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"FR1710033970"}
EXPECTED_FAMILIES = {
    "integrated_application_suite", "federated_security_sso",
    "role_based_access", "enterprise_portal", "configurable_homepages",
    "integration_orchestration", "api_gateway", "document_management",
    "data_lake_metadata", "financial_management", "supply_management",
    "expense_management", "manufacturing_erp", "supplier_collaboration",
    "human_capital_management", "core_hr", "talent_management",
    "workforce_management", "payroll", "asset_management",
    "maintenance_management", "business_intelligence",
    "enterprise_performance_management", "governance_risk_compliance",
}
# The category's expected centre and neighbours, checked as token
# absences against the fork's own words. "fee" is checked at word
# level because its only substring occurrence is inside
# "feedback" (the d/EPM sentence).
ABSENT_TOKENS = (
    "enterprise resource planning", "customer relationship",
    "sales order", "order management", "tax", "budget", "grant",
    "training", "e-commerce", "ecommerce", "help desk",
    "point of sale", "treasury", "reconcil",
)
ABSENT_WORDS = ("crm", "score", "fee", "price")


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
        report = load("remainder/nosignal_report.json")
        recs = report if isinstance(report, list) else (
            report.get("forks") or list(report.values()))
        cls.resolution = {r["fork_id"]: r for r in recs}

    def test_membership_is_exactly_the_resolved_fork(self):
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)
        unit = next(u for u in self.census["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn("FR1710033970", unit["fork_ids"])
        census_fork = next(f for f in self.census["forks"]
                           if f["fork_id"] == "FR1710033970")
        self.assertTrue(census_fork["no_signal"])
        self.assertEqual(census_fork["citations"], [])

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["FR1710033970"]
        row = self.registry["FR1710033970"]
        self.assertEqual(sheet["vendor"], row["vendor"])
        self.assertEqual(sheet["product"], row["product"])
        self.assertEqual(sheet["vendor"], "Infor")
        self.assertEqual(
            sheet["product"],
            "Infor Government Solutions (IGS) Software as a Service")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["deadramp_category"],
                         "Enterprise Resource Planning")
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_classification_citation_matches_the_resolution(self):
        sheet = self.sheets["FR1710033970"]
        resolution = self.resolution["FR1710033970"]
        self.assertEqual(resolution["status"], "resolved")
        self.assertEqual(resolution["category_proposal"],
                         "Enterprise Resource Planning")
        self.assertTrue(resolution["is_new_category"])
        self.assertEqual(sheet["classification_evidence"],
                         resolution["evidence_sentence"])
        self.assertEqual(sheet["classification_source_url"],
                         resolution["source_url"])
        self.assertEqual(
            sheet["classification_source_url"],
            "https://www.infor.com/resources/infor-government-saas-overview")
        # The two evidence streams never mix: the classification
        # sentence is the vendor's brochure prose, not marketplace
        # text, and it is evidence for no claim.
        self.assertNotIn(sheet["classification_evidence"],
                         sheet["description"])
        for claim in sheet["functions_claimed"]:
            self.assertNotEqual(claim["evidence"],
                                sheet["classification_evidence"])

    def test_claims_match_the_taxonomy(self):
        sheet = self.sheets["FR1710033970"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        self.assertEqual(claimed, EXPECTED_FAMILIES)
        self.assertEqual(len(sheet["functions_claimed"]), 24)

    def test_evidence_is_verbatim(self):
        sheet = self.sheets["FR1710033970"]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"],
                          claim["function_id"])

    def test_checked_absences_hold(self):
        description = self.sheets["FR1710033970"]["description"].lower()
        for token in ABSENT_TOKENS:
            self.assertNotIn(token, description, token)
        for word in ABSENT_WORDS:
            self.assertIsNone(re.search(r"\b%s\b" % word, description),
                              word)
        # The category's own name never occurs in full: the
        # description says "Manufacturing ERP", "Infor ERP
        # solutions", and "an end-to-end ERP solution" -- the
        # category rests on the suite framing, not on the phrase.
        self.assertIn("manufacturing erp", description)
        self.assertEqual(description.count("fee"), 1)
        self.assertIn("feedback", description)


if __name__ == "__main__":
    unittest.main()
