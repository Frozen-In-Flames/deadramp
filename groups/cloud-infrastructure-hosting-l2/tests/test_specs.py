"""Spec integrity for Remainder Group 4 (Cloud Infrastructure &
Hosting L2): membership, tier fields, the literal claim tables,
verbatim claim evidence in the cached descriptions, the SAP
catalogue exclusion, and the classification fields pinned against
remainder/nosignal_report.json.

The classification-vs-claims split is pinned mechanically: for all
six forks the live-doc classification sentence does NOT occur in
the cached marketplace description, and no claim's evidence is the
classification sentence — classification and claims are separate
evidence streams and never mix.
"""

import json
import os
import unittest

GROUP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(GROUP))

MEMBERS = [
    "FR2004446306",
    "F1208031461",
    "F1510137547",
    "F1602257856",
    "FR1719841002",
    "AGENCYWC2",
]

EXPECTED_RECORDS = {
    "FR2004446306": ("Elastic", "Elastic Cloud", ["SaaS"],
                     "Government Community Cloud"),
    "F1208031461": ("IBM", "IBM Platform Services for Government",
                    ["SaaS", "PaaS"], "Public Cloud"),
    "F1510137547": ("Rackspace Government Solutions",
                    "Rackspace Government Cloud", ["PaaS"],
                    "Government Community Cloud"),
    "F1602257856": ("SAP National Security Services Inc. (SAP NS2)",
                    "DoD Cloud Intelligent Enterprise \u2013 DD-CIE",
                    ["SaaS"], "Government Community Cloud"),
    "FR1719841002": ("SAP National Security Services Inc. (SAP NS2)",
                     "SAP NS2 Cloud Intelligent Enterprise",
                     ["PaaS", "SaaS"], "Government Community Cloud"),
    "AGENCYWC2": ("United States Department of the Treasury",
                  "Treasury Cloud Moderate", ["PaaS", "SaaS"],
                  "Government Community Cloud"),
}

EXPECTED_CLAIMS = {
    "FR2004446306": ["hosting_platform", "deployment_configuration",
                     "infrastructure_providers", "identity_access",
                     "encryption"],
    "F1208031461": ["multi_tenancy", "monitoring_observability",
                    "identity_access", "resource_optimization",
                    "ai_recommendations"],
    "F1510137547": ["hosting_platform", "dedicated_environments",
                    "infrastructure_providers", "monitoring_observability",
                    "security_services", "backup_disaster_recovery",
                    "managed_operations", "us_operations_residency",
                    "compliance_authorization_support"],
    "F1602257856": ["hosting_platform"],
    "FR1719841002": ["hosting_platform", "us_operations_residency"],
    "AGENCYWC2": ["hosting_platform", "dedicated_environments",
                  "multi_tenancy", "deployment_configuration",
                  "infrastructure_providers", "monitoring_observability",
                  "security_services", "backup_disaster_recovery",
                  "identity_access", "managed_operations",
                  "account_provisioning", "content_delivery"],
}

EXPECTED_HISTOGRAM = {
    "hosting_platform": 5,
    "dedicated_environments": 2,
    "multi_tenancy": 2,
    "deployment_configuration": 2,
    "infrastructure_providers": 3,
    "monitoring_observability": 3,
    "security_services": 2,
    "backup_disaster_recovery": 2,
    "identity_access": 3,
    "encryption": 1,
    "managed_operations": 2,
    "us_operations_residency": 2,
    "resource_optimization": 1,
    "ai_recommendations": 1,
    "account_provisioning": 1,
    "compliance_authorization_support": 1,
    "content_delivery": 1,
}

SHEET_KEYS = {
    "fork_id", "vendor", "product", "service_model", "deployment_model",
    "fedramp_impact_level", "cmmc_tier", "authorization_status",
    "business_categories_in_source", "deadramp_category", "description",
    "functions_claimed", "classification_evidence",
    "classification_source_url", "source", "source_url",
}

CATALOGUE_LEADINS = (
    "SAP S/4HANA", "SAP SuccessFactors",
    "SAP Business Technology Platform", "SAP HANA Cloud",
    "SAP Analytics Cloud", "SAP Integrated Business Planning",
    "SAP Fieldglass", "Includes:",
)


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestSpecs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sheets = _load(os.path.join(GROUP, "specs", "specs.json"))
        cls.by_id = {s["fork_id"]: s for s in cls.sheets}
        cls.uncovered = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "uncovered.json"))}
        cls.report = {r["fork_id"]: r for r in _load(
            os.path.join(REPO, "remainder", "nosignal_report.json"))}
        cls.registry = {r["source_url"].rstrip("/").rsplit("/", 1)[-1]: r
                        for r in _load(os.path.join(REPO, "forks.json"))}

    def test_membership_exact(self):
        self.assertEqual(sorted(self.by_id), sorted(MEMBERS))
        self.assertEqual(len(self.sheets), 6)

    def test_sheet_schema_keys(self):
        for sheet in self.sheets:
            self.assertEqual(set(sheet.keys()), SHEET_KEYS, sheet["fork_id"])

    def test_record_fields(self):
        for fork_id, (vendor, product, models, deployment) in \
                EXPECTED_RECORDS.items():
            sheet = self.by_id[fork_id]
            self.assertEqual(sheet["vendor"], vendor, fork_id)
            self.assertEqual(sheet["product"], product, fork_id)
            self.assertEqual(sheet["service_model"], models, fork_id)
            self.assertEqual(sheet["deployment_model"], deployment, fork_id)
            self.assertEqual(
                sheet["source_url"], self.registry[fork_id]["source_url"])

    def test_tier_fields_from_marketplace_record(self):
        for sheet in self.sheets:
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
            self.assertEqual(
                sheet["deadramp_category"], "Cloud Infrastructure & Hosting")
            # The census recorded no business function for these forks.
            self.assertEqual(sheet["business_categories_in_source"], [])

    def test_descriptions_match_census_copies(self):
        for fork_id in MEMBERS:
            self.assertEqual(
                self.by_id[fork_id]["description"],
                self.uncovered[fork_id]["description"], fork_id)

    def test_literal_claim_tables(self):
        for fork_id, expected in EXPECTED_CLAIMS.items():
            actual = [c["function_id"]
                      for c in self.by_id[fork_id]["functions_claimed"]]
            self.assertEqual(actual, expected, fork_id)

    def test_claim_totals_and_histogram(self):
        total = sum(len(s["functions_claimed"]) for s in self.sheets)
        self.assertEqual(total, 34)
        histogram = {}
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                histogram[claim["function_id"]] = \
                    histogram.get(claim["function_id"], 0) + 1
        self.assertEqual(histogram, EXPECTED_HISTOGRAM)

    def test_no_zero_claim_forks(self):
        for sheet in self.sheets:
            self.assertGreater(len(sheet["functions_claimed"]), 0,
                               sheet["fork_id"])

    def test_claim_evidence_verbatim_in_description(self):
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              (sheet["fork_id"], claim["function_id"]))
                self.assertGreater(len(claim["evidence"]), 0)

    def test_classification_fields_match_report(self):
        for fork_id in MEMBERS:
            sheet = self.by_id[fork_id]
            row = self.report[fork_id]
            self.assertEqual(row["status"], "resolved")
            self.assertEqual(
                row["category_proposal"], "Cloud Infrastructure & Hosting")
            self.assertTrue(row["is_new_category"])
            self.assertEqual(
                sheet["classification_evidence"], row["evidence_sentence"])
            self.assertEqual(
                sheet["classification_source_url"], row["source_url"])

    def test_classification_and_claims_never_mix(self):
        # For all six forks the classification sentence does not
        # occur in the cached description at all, and no claim's
        # evidence is the classification sentence.
        for sheet in self.sheets:
            self.assertNotIn(
                sheet["classification_evidence"], sheet["description"],
                sheet["fork_id"])
            for claim in sheet["functions_claimed"]:
                self.assertNotEqual(
                    claim["evidence"], sheet["classification_evidence"])

    def test_sap_catalogue_exclusion(self):
        # No SAP claim evidence is drawn from a hosted-application
        # catalogue unit; the catalogue's business vocabulary
        # (payroll, human capital) appears in the descriptions but
        # in no claim.
        for fork_id in ("F1602257856", "FR1719841002"):
            sheet = self.by_id[fork_id]
            self.assertIn("payroll", sheet["description"].lower())
            for claim in sheet["functions_claimed"]:
                self.assertFalse(
                    claim["evidence"].startswith(CATALOGUE_LEADINS),
                    (fork_id, claim["function_id"]))
                self.assertNotIn("payroll", claim["evidence"].lower())
                self.assertNotIn("human capital", claim["evidence"].lower())

    def test_ddcie_residency_sentence_artifact(self):
        # DD-CIE's description carries the U.S.-citizen operations
        # sentence verbatim, but the house sentence split cuts it
        # after "U.S.", so no residency pattern survives whole and
        # the fork claims hosting only. Recorded, not repaired.
        sheet = self.by_id["F1602257856"]
        self.assertIn("operated exclusively by U.S. citizens",
                      sheet["description"])
        claimed = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertNotIn("us_operations_residency", claimed)
        self.assertEqual(claimed, ["hosting_platform"])

    def test_absent_technology_tokens(self):
        for sheet in self.sheets:
            text = sheet["description"].lower()
            for token in ("kubernetes", "serverless", "docker",
                          "terraform", "ansible"):
                self.assertNotIn(token, text, (sheet["fork_id"], token))

    def test_near_miss_tokens_confined(self):
        # "machine learning" occurs only in Elastic's description
        # (a hosted-stack feature name; it fires no family) and
        # "endpoint management" only in IBM's (the MaaS360
        # component; the MDM category's ground, not this one's).
        for sheet in self.sheets:
            text = sheet["description"].lower()
            if sheet["fork_id"] == "FR2004446306":
                self.assertIn("machine learning", text)
            else:
                self.assertNotIn("machine learning", text, sheet["fork_id"])
            if sheet["fork_id"] == "F1208031461":
                self.assertIn("endpoint management", text)
            else:
                self.assertNotIn("endpoint management", text, sheet["fork_id"])


if __name__ == "__main__":
    unittest.main()
