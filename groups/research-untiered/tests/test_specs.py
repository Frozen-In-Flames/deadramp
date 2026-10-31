"""Spec-sheet pins for the Research untiered set (Untiered Set 9).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 4 sheets, membership exact against
census unit ``untiered:Research`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, and the literal result of the
verbatim taxonomy application — **zero claims across the set,
all four forks zero-claim** — so a future re-extraction that
quietly re-tunes the taxonomy, or a sheet edit that manufactures
a claim, fails here instead of drifting.
"""

import json
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Research"
EXPECTED_ZERO_CLAIM = [
    "FR2632054521",   # Leadership Connect
    "FR2632054491",   # OpenClinica4 (OC4)
    "FR2701557049",   # Sixtyfour Identity Intelligence Platform
    "FR2631747315",   # Sustainment Digital Manufacturing Hub
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

    def test_exactly_four_sheets(self):
        self.assertEqual(len(self.specs), 4)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(set(self.by_id), set(self.unit_ids))
        self.assertEqual(len(self.unit_ids), 4)

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"], "Research",
                             sheet["fork_id"])

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
        # Recorded as-is from the source record. Three of the four
        # carry "Research" among their source business categories;
        # Sustainment (FR2631747315) does NOT — its census
        # assignment to Research rests on its description's
        # market-research function alone. Both facts are pinned.
        expected = {
            "FR2632054521": ["Analytics", "Artificial Intelligence (AI)",
                             "Collaboration",
                             "Customer Relations Management (CRM)",
                             "Customer Service", "Data Management",
                             "Legal & Policy", "Marketing & Sales",
                             "Operations Management", "Research"],
            "FR2632054491": ["Health & Wellness", "Research",
                             "Data Management", "Analytics"],
            "FR2701557049": ["Artificial Intelligence (AI)",
                             "Marketing & Sales", "Research"],
            "FR2631747315": ["Operations Management", "Collaboration",
                             "Analytics", "Artificial Intelligence (AI)",
                             "Data Management"],
        }
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["business_categories_in_source"],
                             expected[fid], fid)

    def test_descriptions_equal_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"], fid)
            self.assertNotIn("\r", sheet["description"], fid)

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

    def test_census_citations_verify_verbatim(self):
        verified = 0
        total = 0
        for fid, sheet in self.by_id.items():
            for citation in self.census[fid].get("citations") or []:
                total += 1
                self.assertIn(citation, sheet["description"], fid)
                verified += 1
        self.assertEqual((verified, total), (6, 6))


if __name__ == "__main__":
    unittest.main()
