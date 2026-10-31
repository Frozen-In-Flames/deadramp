"""Spec-sheet tests for the untiered Talent Development set.

These tests pin the claims in ``specs/specs.json`` to the source
descriptions and to the taxonomy defined in
``scratch/extract.py`` — which is derived fresh from these two
forks' own descriptions, because Talent Development is a new
category with no tiered group and therefore no inherited
taxonomy. They also pin the untiered tier discipline: every
sheet's FedRAMP impact level is exactly the source's
(``Unknown``) and ``cmmc_tier`` is ``null``.

A census citation verifying is not a claim: each fork's single
census citation verifies against its description, and neither
serves as claim evidence — BetterUp's cites its positioning
sentence; FORGE's cites its full sentence while the claim
evidence of record is that sentence's first fragment under the
founding sentence split (see scratch/ARTIFACTS.md).
"""

import json
import os
import re
import unittest

GROUP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ROOT = os.path.abspath(os.path.join(GROUP, "..", ".."))

EXPECTED_FORKS = {
    "FR2318956176": {
        "vendor": "BetterUp, Inc.",
        "product": "BetterUp for Government",
        "status": "FedRAMP In Process",
        "filed_category": "Uncategorized (none in source)",
    },
    "FR2635930421": {
        "vendor": "SOFware LLC",
        "product": "FORGE",
        "status": "Initial Implementation",
        "filed_category": "Talent Development",
    },
}

EXPECTED_FAMILIES = {
    "behavioral_mindset_development",
    "workforce_analytics",
    "workforce_assessment",
    "talent_development",
    "decision_support",
}

EXPECTED_CLAIMS = {
    "FR2318956176": {"behavioral_mindset_development", "workforce_analytics"},
    "FR2635930421": {"workforce_assessment", "talent_development",
                     "decision_support"},
}

EXPECTED_TOTALS = {"forks": 2, "claims": 5}

# Functions a reader would expect in a category called Talent
# Development that NEITHER fork's description states. Verified
# token-absent (case-insensitive) across both descriptions,
# here and in scratch/extract.py.
ABSENT_TOKENS = [
    "coach", "mentor", "training", "course", "curriculum",
    "learning", "skill", "competen", "succession", "career",
    "appraisal", "engagement", "certif", "feedback", "score",
    "scoring", "artificial intelligence", "encrypt", "audit",
    "security", "access control", "single sign-on",
]


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
                      if u["unit_id"] == "untiered:Talent Development"]
        assert len(unit_forks) == 1
        cls.unit_ids = unit_forks[0]["fork_ids"]
        cls.registry = {f["source_url"].rstrip("/").split("/")[-1]: f
                        for f in load_json(ROOT, "forks.json")}
        cls.census = {r["fork_id"]: r
                      for r in load_json(ROOT, "remainder.json")["forks"]}
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

    def test_tier_discipline_on_every_sheet(self):
        # Untiered: the source publishes no baseline for these
        # forks. Impact stays exactly "Unknown" and cmmc_tier
        # stays null; no tier is assigned anywhere in the set.
        for fork_id, sheet in self.sheets.items():
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             fork_id)
            self.assertIsNone(sheet["cmmc_tier"], fork_id)
            self.assertNotIn("CMMC L", json.dumps(sheet), fork_id)

    def test_recorded_fields_match_registry(self):
        for fork_id, sheet in self.sheets.items():
            record = self.registry[fork_id]
            self.assertEqual(sheet["vendor"], record["vendor"])
            self.assertEqual(sheet["product"], record["product"])
            self.assertEqual(sheet["authorization_status"],
                             EXPECTED_FORKS[fork_id]["status"])
            self.assertEqual(record["fedramp_impact_level"], "Unknown")
            self.assertIsNone(record["cmmc_tier"])
            self.assertEqual(record["category"],
                             EXPECTED_FORKS[fork_id]["filed_category"])
            self.assertEqual(sheet["deadramp_category"],
                             "Talent Development")

    def test_taxonomy_is_the_sets_own_five_families(self):
        self.assertEqual(self.taxonomy_ids, EXPECTED_FAMILIES)
        self.assertEqual(len(self.taxonomy_ids), 5)
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
        # Distinct claim tuples: BetterUp and FORGE share no family.
        self.assertFalse(
            EXPECTED_CLAIMS["FR2318956176"] & EXPECTED_CLAIMS["FR2635930421"])

    def test_every_evidence_sentence_is_in_the_description(self):
        for fork_id, sheet in self.sheets.items():
            normalized = ws(sheet["description"])
            for claim in sheet["functions_claimed"]:
                self.assertIn(ws(claim["evidence"]), normalized,
                              "%s/%s" % (fork_id, claim["function_id"]))

    def test_development_kinds_are_not_merged(self):
        # Each fork claims development only in its own words:
        # BetterUp does not claim talent_development and FORGE does
        # not claim behavioral_mindset_development.
        betterup = {c["function_id"]
                    for c in self.sheets["FR2318956176"]["functions_claimed"]}
        forge = {c["function_id"]
                 for c in self.sheets["FR2635930421"]["functions_claimed"]}
        self.assertNotIn("talent_development", betterup)
        self.assertNotIn("behavioral_mindset_development", forge)
        # And the phrases themselves are absent from the other
        # fork's description.
        self.assertNotIn("talent development",
                         self.sheets["FR2318956176"]["description"].lower())
        self.assertNotIn("behavioral and mindset development",
                         self.sheets["FR2635930421"]["description"].lower())

    def test_census_citations_verify_but_are_not_claims(self):
        total = verified = evidence = 0
        for fork_id, report in self.citation_check.items():
            total += report["census"]
            verified += report["verified"]
            evidence += sum(1 for d in report["details"]
                            if d["serves_as_claim_evidence"])
            # Each fork carries exactly one census citation and it
            # verifies against the description.
            self.assertEqual(report["census"], 1, fork_id)
            self.assertEqual(report["verified"], 1, fork_id)
            self.assertEqual(len(self.census[fork_id]["citations"]), 1)
        self.assertEqual((total, verified), (2, 2))
        # Neither citation serves as claim evidence: BetterUp's
        # cites its positioning sentence (not evidence for any
        # claim); FORGE's cites its complete sentence while the
        # claim evidence is that sentence's first fragment under
        # the founding split. Both directions are recorded in
        # scratch/ARTIFACTS.md.
        self.assertEqual(evidence, 0)

    def test_certified_services_record_field_never_matched(self):
        notes = {n["fork_id"]: n for n in self.certified_notes}
        self.assertEqual(notes["FR2318956176"]["services"], [])
        # FORGE's field names the product itself and restates its
        # three functions; it was recorded, never matched, and
        # matching it would have changed no claim.
        self.assertEqual(notes["FR2635930421"]["services"], ["FORGE"])

    def test_absent_tokens_absent_from_both_descriptions(self):
        self.assertEqual(self.absence_check["failures"], [])
        for sheet in self.sheets.values():
            lowered = sheet["description"].lower()
            for token in ABSENT_TOKENS:
                self.assertNotIn(token, lowered,
                                 "%s in %s" % (token, sheet["fork_id"]))
            self.assertIsNone(re.search(r"\bai\b", sheet["description"],
                                        re.I))
            self.assertIsNone(re.search(r"\breview\b",
                                        sheet["description"], re.I))


if __name__ == "__main__":
    unittest.main()
