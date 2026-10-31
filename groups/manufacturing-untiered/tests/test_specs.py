"""Spec-sheet tests for the untiered Manufacturing set.

These tests pin the claim in ``specs/specs.json`` to the source
description and to the taxonomy defined in ``scratch/extract.py``
— which is derived fresh from this fork's own description,
because Manufacturing is a new category with no tiered group and
therefore no inherited taxonomy. They also pin the untiered tier
discipline: the sheet's FedRAMP impact level is exactly the
source's (``Unknown``) and ``cmmc_tier`` is ``null``.

A census citation verifying is not automatically a claim — in
either direction. In this set both census citations verify AND
both serve as claim evidence (the census cited exactly the two
sentences the taxonomy was derived from); that is recorded here
as this set's direction, not smoothed into the opposite pattern
other sets recorded.
"""

import json
import os
import re
import unittest

GROUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ROOT = os.path.abspath(os.path.join(GROUP, "..", ".."))

EXPECTED_FORKS = {
    "FR2632054516": {
        "vendor": "Neuramill, Inc.",
        "product": "NeuraBridge",
        "status": "Initial Implementation",
        "filed_category": "Uncategorized (none in source)",
    },
}

EXPECTED_FAMILIES = {
    "manufacturing_intelligence",
    "engineering_intent",
    "intent_transformation",
    "manufacturable_decisions",
}

EXPECTED_CLAIMS = {
    "FR2632054516": {
        "manufacturing_intelligence",
        "engineering_intent",
        "intent_transformation",
        "manufacturable_decisions",
    },
}

EXPECTED_TOTALS = {"forks": 1, "claims": 4}

DESCRIPTION = (
    "NeuraBridge is intelligence software for high-precision "
    "manufacturing. It transforms engineering intent into "
    "structured, manufacturable decisions for aerospace and "
    "defense teams.")

# Functions a reader would expect in a category called
# Manufacturing that the description does NOT state. Verified
# token-absent (case-insensitive) in the description, here and in
# scratch/extract.py.
ABSENT_TOKENS = [
    "design", "lifecycle", "execution system", "quality",
    "inspection", "metrology", "tolerance", "machining",
    "machine tool", "supply", "inventory", "scheduling",
    "production planning", "twin", "simulation", "robot",
    "export", "analytics", "dashboard", "reporting", "workflow",
    "automation", "maintenance", "repair", "sensor", "security",
    "access control", "audit", "encrypt", "single sign-on",
    "score", "scoring", "price", "fee", "cost", "budget",
]
ABSENT_REGEXES = [r"\bai\b", r"\bcad\b", r"\bmes\b", r"\bplm\b",
                  r"\bitar\b", r"\bcnc\b"]


def load_json(*parts):
    with open(os.path.join(*parts), encoding="utf-8") as fh:
        return json.load(fh)


def ws(t):
    return re.sub(r"\s+", " ", t)


class TestSpecs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = load_json(GROUP, "specs", "specs.json")
        cls.sheets = {s["fork_id"]: s for s in cls.specs}
        unit_forks = [u for u in load_json(ROOT, "remainder.json")["build_units"]
                      if u["unit_id"] == "untiered:Manufacturing"]
        assert len(unit_forks) == 1
        cls.unit = unit_forks[0]
        cls.unit_ids = cls.unit["fork_ids"]
        cls.registry = {f["source_url"].rstrip("/").split("/")[-1]: f
                        for f in load_json(ROOT, "forks.json")}
        cls.census = {r["fork_id"]: r
                      for r in load_json(ROOT, "remainder.json")["forks"]}
        cls.uncovered = {u["fork_id"]: u for u in load_json(
            ROOT, "remainder", "uncovered.json")}
        sys_path_fixed = os.path.join(GROUP, "scratch")
        import sys
        if sys_path_fixed not in sys.path:
            sys.path.insert(0, sys_path_fixed)
        import extract  # noqa: E402 -- runs the full extraction pass
        cls.taxonomy_ids = {t[0] for t in extract.TAXONOMY}
        cls.citation_check = load_json(GROUP, "scratch", "citation_check.json")
        cls.function_counts = load_json(GROUP, "scratch",
                                        "function_counts.json")
        cls.absence_check = load_json(GROUP, "scratch", "absence_check.json")
        cls.certified_notes = load_json(GROUP, "scratch",
                                        "certified_services_notes.json")

    def test_membership_matches_census_unit_exactly(self):
        self.assertEqual(set(self.sheets), set(self.unit_ids))
        self.assertEqual(set(self.sheets), set(EXPECTED_FORKS))
        self.assertEqual(len(self.specs), EXPECTED_TOTALS["forks"])
        self.assertIsNone(self.unit["tier"])
        self.assertEqual(self.unit["kind"], "untiered_set")

    def test_tier_discipline_on_the_sheet(self):
        # Untiered: the source publishes no baseline for this fork.
        # Impact stays exactly "Unknown" and cmmc_tier stays null;
        # no tier is assigned anywhere in the set.
        sheet = self.sheets["FR2632054516"]
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertNotIn("CMMC L", json.dumps(sheet))

    def test_recorded_fields_match_registry(self):
        sheet = self.sheets["FR2632054516"]
        record = self.registry["FR2632054516"]
        self.assertEqual(sheet["vendor"], record["vendor"])
        self.assertEqual(sheet["product"], record["product"])
        self.assertEqual(sheet["authorization_status"],
                         EXPECTED_FORKS["FR2632054516"]["status"])
        self.assertEqual(record["fedramp_impact_level"], "Unknown")
        self.assertIsNone(record["cmmc_tier"])
        self.assertEqual(record["category"],
                         EXPECTED_FORKS["FR2632054516"]["filed_category"])
        self.assertEqual(sheet["deadramp_category"], "Manufacturing")

    def test_census_proposed_the_new_category(self):
        census = self.census["FR2632054516"]
        self.assertEqual(census["proposed_category"], "Manufacturing")
        self.assertTrue(census["proposed_category_is_new"])
        self.assertFalse(census["no_signal"])
        self.assertEqual(census["build_unit"], "untiered:Manufacturing")

    def test_description_is_the_source_description(self):
        sheet = self.sheets["FR2632054516"]
        self.assertEqual(sheet["description"], DESCRIPTION)
        self.assertEqual(self.uncovered["FR2632054516"]["description"],
                         DESCRIPTION)

    def test_taxonomy_is_the_sets_own_four_families(self):
        self.assertEqual(self.taxonomy_ids, EXPECTED_FAMILIES)
        self.assertEqual(len(self.taxonomy_ids), 4)
        # Function counts cover exactly the taxonomy, nothing else.
        self.assertEqual(set(self.function_counts), EXPECTED_FAMILIES)
        for family_id, count in self.function_counts.items():
            self.assertEqual(count, 1, family_id)

    def test_claims_match_expectations_exactly(self):
        total = 0
        for fork_id, expected in EXPECTED_CLAIMS.items():
            got = {c["function_id"]
                   for c in self.sheets[fork_id]["functions_claimed"]}
            self.assertEqual(got, expected, fork_id)
            self.assertTrue(got <= self.taxonomy_ids, fork_id)
            total += len(got)
        self.assertEqual(total, EXPECTED_TOTALS["claims"])
        # No zero-claim forks in this set.
        for fork_id, sheet in self.sheets.items():
            self.assertTrue(sheet["functions_claimed"], fork_id)

    def test_every_evidence_sentence_is_in_the_description(self):
        for fork_id, sheet in self.sheets.items():
            normalized = ws(sheet["description"])
            for claim in sheet["functions_claimed"]:
                self.assertIn(ws(claim["evidence"]), normalized,
                              "%s/%s" % (fork_id, claim["function_id"]))

    def test_evidence_sentences_are_the_two_source_sentences(self):
        sheet = self.sheets["FR2632054516"]
        evidence = {c["function_id"]: c["evidence"]
                    for c in sheet["functions_claimed"]}
        s1 = ("NeuraBridge is intelligence software for "
              "high-precision manufacturing.")
        s2 = ("It transforms engineering intent into structured, "
              "manufacturable decisions for aerospace and defense "
              "teams.")
        self.assertEqual(evidence["manufacturing_intelligence"], s1)
        for family in ("engineering_intent", "intent_transformation",
                       "manufacturable_decisions"):
            self.assertEqual(evidence[family], s2, family)

    def test_census_citations_verify_and_serve_as_evidence(self):
        total = verified = evidence = 0
        for fork_id, report in self.citation_check.items():
            total += report["census"]
            verified += report["verified"]
            evidence += sum(1 for d in report["details"]
                            if d["serves_as_claim_evidence"])
            self.assertEqual(report["census"], 2, fork_id)
            self.assertEqual(report["verified"], 2, fork_id)
            self.assertEqual(report["failed"], [], fork_id)
        self.assertEqual((total, verified), (2, 2))
        # This set's direction: both census citations are exactly
        # the two sentences the taxonomy derives from, so both
        # serve as claim evidence. Verification alone is still not
        # what makes them claims — the taxonomy matches are.
        self.assertEqual(evidence, 2)

    def test_certified_services_record_field_never_matched(self):
        notes = {n["fork_id"]: n for n in self.certified_notes}
        self.assertEqual(notes["FR2632054516"]["services"], [])

    def test_absent_tokens_absent_from_the_description(self):
        self.assertEqual(self.absence_check["failures"], [])
        lowered = self.sheets["FR2632054516"]["description"].lower()
        for token in ABSENT_TOKENS:
            self.assertNotIn(token, lowered, token)
        description = self.sheets["FR2632054516"]["description"]
        for pattern in ABSENT_REGEXES:
            self.assertIsNone(re.search(pattern, description, re.I),
                              pattern)


if __name__ == "__main__":
    unittest.main()
