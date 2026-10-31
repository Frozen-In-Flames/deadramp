"""Spec-sheet pins for the Legal & Policy untiered set (Untiered Set 12).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 3 sheets, membership exact against
census unit ``untiered:Legal & Policy`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, and the literal result of the
verbatim taxonomy application — **zero claims across the set,
all three forks zero-claim** — so a future re-extraction that
quietly re-tunes the taxonomy, or a sheet edit that manufactures
a claim, fails here instead of drifting. The taxonomy is the
founding fork's own phrases; the founding group's six tiered
additions also claimed zero under it, and this set's zero is the
same honest outcome, pinned rather than repaired.
"""

import json
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Legal & Policy"
EXPECTED_ZERO_CLAIM = [
    "FR2009476860",   # Casepoint Government
    "FR2701247925",   # Litmas AI
    "FR2633734932",   # Alira
]


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


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

    def test_exactly_three_sheets(self):
        self.assertEqual(len(self.specs), 3)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(set(self.by_id), set(self.unit_ids))
        self.assertEqual(len(self.unit_ids), 3)

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"], "Legal & Policy",
                             sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["service_model"],
                             [reg["service_model"]], fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)

    def test_business_categories_recorded_as_in_source(self):
        # Recorded as-is from the source record. Only Litmas is
        # filed under Legal & Policy in its own business
        # categories; Casepoint carries none at all and Alira is
        # filed Analytics-first — all three sit in this category
        # because the census assigned them from their own
        # descriptions. Both facts are pinned.
        expected = {
            "FR2009476860": [],
            "FR2701247925": ["Legal & Policy",
                             "Artificial Intelligence (AI)", "Research"],
            "FR2633734932": ["Analytics", "Collaboration",
                             "Data Management",
                             "Content Management System (CMS)",
                             "Legal & Policy",
                             "Artificial Intelligence (AI)"],
        }
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["business_categories_in_source"],
                             expected[fid], fid)

    def test_descriptions_equal_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"], fid)
        # Casepoint's source description carries "\r\n" line
        # endings (paragraph breaks and its bulleted list); they
        # are part of the source text and are preserved verbatim,
        # not normalized away. The extractor demonstrated the
        # claim outcome is identical with and without a
        # "\r" -> space normalization (scratch/cr_notes.json).
        self.assertIn("\r", self.by_id["FR2009476860"]["description"])
        self.assertNotIn("\r", self.by_id["FR2701247925"]["description"])
        self.assertNotIn("\r", self.by_id["FR2633734932"]["description"])

    def test_literal_claim_table_zero_claims(self):
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 0)
        for sheet in self.specs:
            self.assertEqual(sheet["functions_claimed"], [],
                             sheet["fork_id"])
        self.assertEqual(
            sorted(s["fork_id"] for s in self.specs
                   if not s["functions_claimed"]),
            sorted(EXPECTED_ZERO_CLAIM))

    def test_certified_services_names_earn_nothing(self):
        # Alira's source record names "Audit Logging and
        # Monitoring" and "Authentication and Access Management"
        # among its certified services. Those are record fields,
        # never matched — the house method matches service_desc
        # only — and they must not surface as claims or as
        # description text.
        alira = self.by_id["FR2633734932"]
        self.assertEqual(alira["functions_claimed"], [])
        self.assertNotIn("Audit Logging and Monitoring",
                         alira["description"])

    def test_census_citations_verify_verbatim(self):
        verified = 0
        total = 0
        for fid, sheet in self.by_id.items():
            for citation in self.census[fid].get("citations") or []:
                total += 1
                self.assertIn(citation, sheet["description"], fid)
                verified += 1
        self.assertEqual((verified, total), (4, 4))


if __name__ == "__main__":
    unittest.main()
