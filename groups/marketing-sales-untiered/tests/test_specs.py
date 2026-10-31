"""Spec integrity: specs/specs.json against the registry and the
remainder census.

Membership must be exactly the census unit's fork set
({FR2700857472, FR2700857469}); every sheet must record tier null
(cmmc_tier None, fedramp_impact_level "Unknown" as in the
source); the taxonomy must be the 13 families defined from these
two descriptions; every claim's evidence sentence must appear in
the fork's description (whitespace-normalized — Zeta's carries
newlines); the census citations must verify; and the checked
absences must hold at token level across both descriptions.
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[1]

EXPECTED_FORKS = {"FR2700857472", "FR2700857469"}
EXPECTED_FAMILIES = {
    "opportunity_discovery", "opportunity_evaluation",
    "capture_pipeline", "proposal_content", "workflow_automation",
    "ai_powered_support", "audience_segmentation", "campaign_authoring",
    "campaign_scheduling", "outbound_email_delivery",
    "suppression_management", "engagement_reporting", "contact_lists",
}
EXPECTED_CLAIMS = {
    "FR2700857472": {"opportunity_discovery", "opportunity_evaluation",
                     "capture_pipeline", "proposal_content",
                     "workflow_automation", "ai_powered_support"},
    "FR2700857469": {"audience_segmentation", "campaign_authoring",
                     "campaign_scheduling", "outbound_email_delivery",
                     "suppression_management", "engagement_reporting",
                     "contact_lists"},
}
ABSENT_TOKENS = (
    "crm", "customer relationship", "lead", "advertis", "social",
    "sms", "text messag", "search engine", "landing page", "a/b test",
    "personali", "analytics", "brand", "webinar", "print",
    "direct mail", "template", "score", "scoring", "encrypt",
    "audit", "access control", "single sign-on", "event", "survey",
    "preference",
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
        unit = units["untiered:Marketing & Sales"]
        self.assertEqual(unit["kind"], "untiered_set")
        self.assertIsNone(unit["tier"])
        self.assertEqual(set(unit["fork_ids"]), EXPECTED_FORKS)
        self.assertEqual(set(self.sheets), EXPECTED_FORKS)

    def test_tier_discipline_on_every_sheet(self):
        for fork_id, sheet in self.sheets.items():
            self.assertIsNone(sheet["cmmc_tier"], fork_id)
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             fork_id)

    def test_recorded_fields_match_registry(self):
        for fork_id, sheet in self.sheets.items():
            row = self.registry[fork_id]
            self.assertEqual(sheet["vendor"], row["vendor"])
            self.assertEqual(sheet["product"], row["product"])
            self.assertEqual(sheet["authorization_status"],
                             row["authorization_status"])
            self.assertEqual(sheet["deadramp_category"],
                             "Marketing & Sales")
        self.assertEqual(self.sheets["FR2700857472"]["vendor"],
                         "CLEATUS, Inc.")
        self.assertEqual(self.sheets["FR2700857469"]["product"],
                         "Zeta Marketing Platform for Government")

    def test_claims_match_the_taxonomy_exactly(self):
        total = 0
        for fork_id, expected in EXPECTED_CLAIMS.items():
            claimed = {c["function_id"]
                       for c in self.sheets[fork_id]["functions_claimed"]}
            self.assertEqual(claimed, expected, fork_id)
            self.assertTrue(claimed <= EXPECTED_FAMILIES)
            total += len(claimed)
        self.assertEqual(total, 13)

    def test_every_evidence_sentence_is_in_the_description(self):
        for fork_id, sheet in self.sheets.items():
            normalized = ws(sheet["description"])
            for claim in sheet["functions_claimed"]:
                self.assertIn(ws(claim["evidence"]), normalized,
                              (fork_id, claim["function_id"]))

    def test_census_citations_verify(self):
        census_forks = {r["fork_id"]: r for r in self.census["forks"]}
        for fork_id, sheet in self.sheets.items():
            citations = census_forks[fork_id]["citations"]
            self.assertEqual(len(citations), 2, fork_id)
            for citation in citations:
                self.assertIn(ws(citation), ws(sheet["description"]),
                              (fork_id, citation[:40]))

    def test_checked_absences_hold_at_token_level(self):
        for fork_id, sheet in self.sheets.items():
            low = sheet["description"].lower()
            for token in ABSENT_TOKENS:
                self.assertNotIn(token, low, (fork_id, token))

    def test_no_baseline_or_equivalence_language_in_sheets(self):
        for fork_id, sheet in self.sheets.items():
            self.assertNotIn("CMMC L", json.dumps(sheet), fork_id)


if __name__ == "__main__":
    unittest.main()
