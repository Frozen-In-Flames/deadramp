"""Spec-sheet pins for the Communication untiered set (Untiered Set 13).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 2 sheets, membership exact against
census unit ``untiered:Communication`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, every claim's evidence verbatim
in its fork's description, and the literal result of the verbatim
taxonomy application — **3 claims across the set (BlackBerry AtHoc:
notifications_alerts; Cisco UCM Cloud: messaging, voice_telephony);
no zero-claim fork** — so a future re-extraction that quietly
re-tunes the taxonomy, or a sheet edit that manufactures a claim,
fails here instead of drifting. The removal pins hold the two
adjudicated removals (founding correction classes 5 and 3, recorded
in scratch/ARTIFACTS.md): the raw hits fired, their sentences are
present, and no claim stands. The near-miss pins hold the recorded
adjudications: substance present in the text, family phrase absent,
no claim issued.
"""

import json
import os
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Communication"
EXPECTED_CLAIMS = {
    "F1302271924": ["notifications_alerts"],          # BlackBerry AtHoc
    "F1604017885": ["messaging", "voice_telephony"],  # Cisco UCM Cloud
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

    def test_exactly_two_sheets(self):
        self.assertEqual(len(self.specs), 2)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(set(self.by_id), set(self.unit_ids))
        self.assertEqual(len(self.unit_ids), 2)

    def test_high_sibling_record_is_not_a_member(self):
        # F1302271924A is the same product's separate High record
        # (filed under Collaboration, CMMC L3-adjacent); Phase 1
        # keeps paired records separate and it is not in this unit.
        self.assertNotIn("F1302271924A", self.by_id)

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"], "Communication",
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
                             self.uncovered[fid]["description"].strip(), fid)

    def test_literal_claim_table(self):
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 3)

    def test_no_zero_claim_forks(self):
        zero = {s["fork_id"] for s in self.specs if not s["functions_claimed"]}
        self.assertEqual(zero, set())

    def test_every_evidence_verbatim_in_description(self):
        for sheet in self.specs:
            # Founding normalization: carriage returns become spaces
            # before sentence-splitting, so evidence is checked
            # against the normalized description.
            norm = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], norm,
                              f"{sheet['fork_id']} {claim['function_id']}")

    # -- Removal pins: the raw hits fired on these sentences; the
    # claims were removed under the founding group's recorded
    # correction classes (scratch/ARTIFACTS.md items R1-R2) and
    # must stay removed. --

    def test_removal_athoc_incident_events_not_scheduling(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("critical events", desc)
        self.assertIn("report events", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("scheduling_events", claimed)

    def test_removal_athoc_self_reporting_not_reporting_analytics(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("self-reporting by individuals", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("reporting_analytics", claimed)

    # -- Near-miss pins: substance present, family phrase absent, no
    # claim issued (scratch/ARTIFACTS.md items N1-N7). --

    def test_nearmiss_athoc_location_visibility_not_tracking(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("real-time visibility into location and status", desc)
        self.assertNotIn("location data", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("tracking_awareness", claimed)

    def test_nearmiss_athoc_permission_based_not_permits(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("permission-based network", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("permits_surveys", claimed)
        self.assertNotIn("identity_access", claimed)

    def test_nearmiss_athoc_call_center_not_voice_telephony(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("call center operators", desc)
        self.assertNotIn("contact center", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("voice_telephony", claimed)

    def test_nearmiss_athoc_securely_not_secure_transmission(self):
        desc = self.by_id["F1302271924"]["description"]
        self.assertIn("communicate and collaborate securely", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1302271924"]["functions_claimed"]]
        self.assertNotIn("secure_transmission", claimed)

    def test_nearmiss_cisco_access_lists_not_identity_access(self):
        desc = self.by_id["F1604017885"]["description"]
        self.assertIn("personalized access lists", desc)
        self.assertNotIn("access control", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1604017885"]["functions_claimed"]]
        self.assertNotIn("identity_access", claimed)

    def test_nearmiss_cisco_video_substance_no_family(self):
        desc = self.by_id["F1604017885"]["description"]
        self.assertIn("immersive video rooms", desc)
        self.assertIn("Conferencing", desc)
        claimed = [c["function_id"]
                   for c in self.by_id["F1604017885"]["functions_claimed"]]
        # No taxonomy family covers video / meetings / presence;
        # the voice half is what voice_telephony tags.
        self.assertEqual(set(claimed), {"messaging", "voice_telephony"})

    def test_nearmiss_cisco_acknowledgement_absent(self):
        desc = self.by_id["F1604017885"]["description"]
        self.assertNotIn("acknowledg", desc.lower())
        claimed = [c["function_id"]
                   for c in self.by_id["F1604017885"]["functions_claimed"]]
        self.assertNotIn("delivery_verification", claimed)


if __name__ == "__main__":
    unittest.main()
