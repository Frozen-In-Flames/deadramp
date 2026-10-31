"""Spec-sheet pins for the Health & Wellness untiered set (Untiered Set 11).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 3 sheets, membership exact against
census unit ``untiered:Health & Wellness`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, every claim's evidence verbatim
in its fork's description, and the literal result of the verbatim
taxonomy application — **1 claim across the set (86Borders
patient_engagement); Elvo and WellHive zero-claim** — so a future
re-extraction that quietly re-tunes the taxonomy, or a sheet edit
that manufactures a claim, fails here instead of drifting. The
near-miss pins hold the recorded adjudications: substance present
in the text, family phrase absent, no claim issued.
"""

import json
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Health & Wellness"
EXPECTED_CLAIMS = {
    "FR2634047811": ["patient_engagement"],   # 86Borders ConnectAllCare
    "FR2633734921": [],                       # Elvo
    "FR1825232355": [],                       # WellHive
}


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
            self.assertEqual(sheet["deadramp_category"], "Health & Wellness",
                             sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)

    def test_descriptions_match_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"], fid)

    def test_literal_claim_table(self):
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 1)

    def test_zero_claim_forks_named(self):
        zero = {s["fork_id"] for s in self.specs if not s["functions_claimed"]}
        self.assertEqual(zero, {"FR2633734921", "FR1825232355"})

    def test_every_evidence_verbatim_in_description(self):
        for sheet in self.specs:
            # Founding normalization: carriage returns become spaces
            # before sentence-splitting, so evidence is checked
            # against the normalized description.
            norm = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], norm,
                              f"{sheet['fork_id']} {claim['function_id']}")

    # -- Near-miss pins: substance present, family phrase absent, no
    # claim issued (scratch/ARTIFACTS.md items 1-8). --

    def test_nearmiss_wellhive_ehr_integration_not_claimed(self):
        desc = self.by_id["FR1825232355"]["description"]
        self.assertIn("integrations with Electronic Health Records", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["FR1825232355"]["functions_claimed"]]
        self.assertNotIn("emr_integration", claimed)

    def test_nearmiss_hosting_prose_not_claimed(self):
        self.assertIn("deployed on AWS Commercial",
                      self.by_id["FR2634047811"]["description"])
        self.assertIn("hosted on AWS GovCloud",
                      self.by_id["FR1825232355"]["description"])
        for fid in ("FR2634047811", "FR1825232355"):
            claimed = [c["function_id"]
                       for c in self.by_id[fid]["functions_claimed"]]
            self.assertNotIn("hosting_platform", claimed, fid)

    def test_nearmiss_elvo_session_metrics_not_claimed(self):
        desc = self.by_id["FR2633734921"]["description"]
        self.assertIn("records objective session metrics", desc)
        self.assertNotIn("clinical metrics", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["FR2633734921"]["functions_claimed"]]
        self.assertNotIn("measurement_data", claimed)

    def test_nearmiss_86borders_scores_not_scorecards(self):
        desc = self.by_id["FR2634047811"]["description"]
        self.assertIn("higher quality scores", desc)
        self.assertNotIn("scorecards", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["FR2634047811"]["functions_claimed"]]
        self.assertNotIn("analysis_reporting", claimed)

    def test_wellhive_moderate_prose_does_not_move_tier(self):
        sheet = self.by_id["FR1825232355"]
        self.assertIn("FedRAMP Moderate authorization", sheet["description"])
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertEqual(sheet["authorization_status"], "FedRAMP In Process")


if __name__ == "__main__":
    unittest.main()
