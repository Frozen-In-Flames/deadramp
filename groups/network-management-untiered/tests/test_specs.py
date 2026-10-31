"""Spec-sheet pins for the Network Management untiered set
(Untiered Set 19).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 2 sheets, membership exact against
census unit ``untiered:Network Management`` in
../../../remainder.json, every sheet recording the source's
impact level as-is ("Unknown") with ``cmmc_tier`` null, every
description equal to the census's recorded description under
the founding normalization (whitespace collapsed — IronWiFi's
paragraph breaks collapse to spaces, the only difference, and
it is pinned as such), and the literal result of the verbatim
taxonomy application — **2 claims across the set, both
``network_management``, no zero-claim fork** — so a future
re-extraction that quietly re-tunes the taxonomy, or a sheet
edit that manufactures a claim, fails here instead of drifting.
The near-miss tokens are pinned too: the phrases whose absence
keeps this set at two claims (``cloud-managed``, ``deploy``,
``open APIs``, ``telemetry data``, ``stores data on U.S.
soil``) occur nowhere in either description.
"""

import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Network Management"
EXPECTED_CLAIMS = {
    "FR2632755834": ["network_management"],   # Armada Platform
    "FR2631154499": ["network_management"],   # IronWiFi
}
ABSENT_PHRASES = [
    "cloud-managed",
    "deploy",
    "optimize networks",
    "network intelligence (AI)",
    "open APIs",
    "integrate and automate processes",
    "customize the monitoring and management",
    "scale",
    "telemetry data",
    "stores data on U.S. soil",
    "devices as part of the offering",
]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _normalize(text):
    """The founding normalization: zero-width characters removed,
    all whitespace collapsed to single spaces."""
    text = text.replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


class TestSpecSheets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.specs = _load(os.path.join(_GROUP_DIR, "specs", "specs.json"))
        cls.by_id = {s["fork_id"]: s for s in cls.specs}
        rem = _load(os.path.join(_ROOT, "remainder.json"))
        unit = [u for u in rem["build_units"] if u["unit_id"] == UNIT_ID]
        assert len(unit) == 1
        cls.unit_ids = unit[0]["fork_ids"]
        cls.census = {r["fork_id"]: r for r in rem["forks"]}
        cls.uncovered = {
            u["fork_id"]: u
            for u in _load(os.path.join(_ROOT, "remainder", "uncovered.json"))
        }
        forks = _load(os.path.join(_ROOT, "forks.json"))
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        cls.registry = {
            r["source_url"].rstrip("/").split("/")[-1]: r for r in rows
        }

    def test_exactly_two_sheets(self):
        self.assertEqual(len(self.specs), 2)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(set(self.by_id), set(self.unit_ids))
        self.assertEqual(len(self.unit_ids), 2)

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"],
                             "Network Management", sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["authorization_status"],
                             "Initial Implementation", fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)

    def test_business_categories_recorded_as_in_source(self):
        # Recorded as-is from the source record. Neither fork is
        # filed under Network Management in forks.json (Armada is
        # filed Fleet Management, IronWiFi Cybersecurity & Risk
        # Management); both carry Network Management among their
        # source business categories, and the category assignment
        # is the census's, from their own descriptions.
        expected = {
            "FR2632755834": ["Fleet Management", "Network Management",
                             "Operations Management"],
            "FR2631154499": ["Cybersecurity & Risk Management",
                             "Network Management"],
        }
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["business_categories_in_source"],
                             expected[fid], fid)
            self.assertEqual(self.registry[fid]["category"],
                             {"FR2632755834": "Fleet Management",
                              "FR2631154499":
                              "Cybersecurity & Risk Management"}[fid], fid)

    def test_descriptions_equal_census_record_under_normalization(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             _normalize(self.uncovered[fid]["description"]),
                             fid)
        # The one whitespace difference in the set is pinned:
        # IronWiFi's recorded description carries paragraph breaks
        # that the founding normalization collapses; Armada's is
        # exact as recorded.
        self.assertEqual(self.by_id["FR2632755834"]["description"],
                         self.uncovered["FR2632755834"]["description"])
        self.assertNotEqual(self.by_id["FR2631154499"]["description"],
                            self.uncovered["FR2631154499"]["description"])
        self.assertIn("\n", self.uncovered["FR2631154499"]["description"])

    def test_literal_claim_table(self):
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 2)
        for fid, sheet in self.by_id.items():
            self.assertEqual(
                [c["function_id"] for c in sheet["functions_claimed"]],
                EXPECTED_CLAIMS[fid], fid)
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"], fid)
        self.assertEqual(
            [s["fork_id"] for s in self.specs if not s["functions_claimed"]],
            [])

    def test_absent_family_phrases_occur_nowhere(self):
        for fid, sheet in self.by_id.items():
            for phrase in ABSENT_PHRASES:
                self.assertNotIn(phrase, sheet["description"],
                                 f"{fid}: {phrase!r}")

    def test_no_tier_smuggled_from_prose(self):
        # IronWiFi's prose asserts a FIPS 199 impact categorization
        # of Moderate while expressly disclaiming a FedRAMP
        # Moderate authorization; its record says Unknown. The
        # prose moves no tier: both facts are pinned together.
        ironwifi = self.by_id["FR2631154499"]
        self.assertIn("FIPS 199 impact categorization Moderate",
                      ironwifi["description"])
        self.assertIn("not a FedRAMP Moderate Authorization",
                      ironwifi["description"])
        self.assertEqual(ironwifi["fedramp_impact_level"], "Unknown")
        self.assertIsNone(ironwifi["cmmc_tier"])

    def test_certified_services_never_matched(self):
        # IronWiFi's certified_services record field names
        # role-based access and reports; the house method matches
        # service_desc only, and no claim in this set rests on a
        # record field. (Armada's field is empty.)
        for sheet in self.specs:
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"],
                              sheet["fork_id"])

    def test_census_citations_verify(self):
        verified = 0
        total = 0
        evidence_citations = 0
        for fid, sheet in self.by_id.items():
            evidence = {c["evidence"] for c in sheet["functions_claimed"]}
            for citation in self.census[fid].get("citations") or []:
                total += 1
                self.assertIn(_normalize(citation), sheet["description"],
                              fid)
                verified += 1
                if _normalize(citation) in evidence:
                    evidence_citations += 1
        self.assertEqual((verified, total), (2, 2))
        # Armada's citation IS its claim evidence sentence;
        # IronWiFi's citation (the works-with-any-access-point
        # sentence) tags nothing. Verification is not a claim, in
        # either direction.
        self.assertEqual(evidence_citations, 1)


if __name__ == "__main__":
    unittest.main()
