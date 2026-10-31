"""Spec integrity: the spec sheets in specs/specs.json are pinned
against the census unit, the cached marketplace dataset, and the
literal claim tables from UNION-SPEC.md.

Traces to: UNION-SPEC.md "How functions were counted" and the
checked absences — membership is exactly the census unit's two
fork IDs, every description is byte-equal to the cache's
service_desc, every claim's evidence is a verbatim substring of
its sheet's description, and the absence tokens the spec names
really are absent from both descriptions.
"""

import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

EXPECTED_CLAIMS = {
    "F1506046707": [
        "contract_lifecycle_management", "regulatory_compliance",
        "audit_support", "vendor_interaction", "protest_response",
        "reporting_analysis", "workflow_standardization", "data_calls",
        "risk_visibility", "commercial_acquisition", "saas_delivery",
    ],
    "F1510017461": [
        "contract_lifecycle_management", "regulatory_compliance",
        "audit_support", "vendor_interaction", "opportunity_portal",
        "opportunity_issuance", "award_management", "bid_submission",
        "reverse_auction", "financial_assistance",
        "subscription_billing", "system_integration",
        "vendor_registration", "secure_communication",
    ],
}


def _load(relpath):
    with open(os.path.join(_REPO_ROOT, relpath), encoding="utf-8") as fh:
        return json.load(fh)


class TestSpecIntegrity(unittest.TestCase):
    """The spec sheets are exactly what the spec claims they are."""

    @classmethod
    def setUpClass(cls):
        with open(os.path.join(_GROUP_ROOT, "specs", "specs.json"),
                  encoding="utf-8") as fh:
            cls.sheets = json.load(fh)
        cls.remainder = _load("remainder.json")
        dump = _load("raw/data_dump.json")
        products = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        cls.cache = {p["id"]: p for p in products
                     if isinstance(p, dict) and "id" in p}

    def test_membership_is_exactly_the_census_unit(self):
        """Specs: sheet fork IDs equal the census unit's fork list,
        in order."""
        unit = None
        for candidate in self.remainder["build_units"]:
            if candidate.get("unit_id") == "new-group:Contract Management|L2":
                unit = candidate
                break
        self.assertIsNotNone(unit)
        self.assertEqual([s["fork_id"] for s in self.sheets],
                         unit["fork_ids"])
        self.assertEqual(len(self.sheets), 2)

    def test_descriptions_byte_equal_to_cache(self):
        """Specs: each sheet's description is the cached
        service_desc verbatim."""
        for sheet in self.sheets:
            record = self.cache[sheet["fork_id"]]
            self.assertEqual(sheet["description"], record["service_desc"],
                             sheet["fork_id"])

    def test_tier_and_category_fields(self):
        """Specs: both forks are Moderate / L2 in the new Contract
        Management category."""
        for sheet in self.sheets:
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["deadramp_category"],
                             "Contract Management")
            self.assertEqual(sheet["vendor"], "Unison")

    def test_literal_claim_tables(self):
        """Specs: the per-fork claimed function ids equal the
        literal tables (11 and 14; 25 total)."""
        total = 0
        for sheet in self.sheets:
            claimed = [c["function_id"] for c in sheet["functions_claimed"]]
            self.assertEqual(claimed, EXPECTED_CLAIMS[sheet["fork_id"]],
                             sheet["fork_id"])
            total += len(claimed)
        self.assertEqual(total, 25)

    def test_taxonomy_has_21_families(self):
        """Specs: the union of claimed families across both sheets
        is the 21-family taxonomy."""
        families = set()
        for sheet in self.sheets:
            families.update(c["function_id"]
                            for c in sheet["functions_claimed"])
        self.assertEqual(len(families), 21)

    def test_every_evidence_is_verbatim(self):
        """Specs: every claim's evidence string appears verbatim in
        its own sheet's description."""
        for sheet in self.sheets:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              (sheet["fork_id"], claim["function_id"]))

    def test_checked_absences_hold(self):
        """Specs: the absence checks named in UNION-SPEC hold
        against both descriptions — no signature, invoice, clause,
        draft, template, evaluation/scoring, surveillance, or
        AI/ML tokens."""
        patterns = [
            r"\bsign", r"\binvoice", r"\bclause", r"\bdraft",
            r"\btemplate", r"\bevaluat", r"\bscoring",
            r"\bsurveillance", r"\bCPARS\b", r"\bAI\b",
            r"machine learning", r"artificial intelligence",
            r"\bAPI\b",
        ]
        for sheet in self.sheets:
            for pattern in patterns:
                self.assertIsNone(
                    re.search(pattern, sheet["description"]),
                    (sheet["fork_id"], pattern))


if __name__ == "__main__":
    unittest.main()
