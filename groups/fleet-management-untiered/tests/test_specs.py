"""Spec-sheet pins for the Fleet Management untiered set (Untiered Set 15).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 2 sheets, membership exact against
census unit ``untiered:Fleet Management`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, every claim's evidence verbatim
in its fork's description, and the literal result of the verbatim
taxonomy application — **4 claims across the set (each fork:
telematics_gps, api_integrations); no zero-claim fork** — so a
future re-extraction that quietly re-tunes the taxonomy, or a
sheet edit that manufactures a claim, fails here instead of
drifting. The removal pins hold the recorded wording artifacts
(scratch/ARTIFACTS.md): the broad vocabulary is present in the
text and no claim stands on it. The near-miss pins hold the
recorded adjudications: substance present, family phrase absent,
no claim issued.
"""

import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Fleet Management"
EXPECTED_CLAIMS = {
    "FR2633153272": ["telematics_gps", "api_integrations"],  # Samsara
    "FR2700857493": ["telematics_gps", "api_integrations"],  # Samsara (duplicate record)
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

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"], "Fleet Management",
                             sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)

    def test_recorded_fields_as_in_source(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["authorization_status"],
                             "Initial Implementation", fid)
            self.assertEqual(sheet["deployment_model"], "Public Cloud", fid)
            self.assertEqual(sheet["service_model"], ["SaaS"], fid)
            self.assertEqual(sheet["business_categories_in_source"],
                             ["Fleet Management", "Operations Management"], fid)

    def test_descriptions_match_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"].strip(), fid)

    def test_literal_claim_table(self):
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 4)

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

    def test_duplicate_pair_sheets_identical_claims(self):
        # The two records are a duplicate pair (same vendor, product,
        # and byte-identical description); Phase 1 keeps paired
        # records separate, and their claim tables are identical.
        a, b = (self.by_id[fid] for fid in self.unit_ids)
        self.assertEqual(a["description"], b["description"])
        self.assertEqual(a["functions_claimed"], b["functions_claimed"])
        self.assertNotEqual(a["fork_id"], b["fork_id"])

    # -- Removal pins: the broad vocabulary is present in the text;
    # the tightened (verbatim) family phrases are absent; no claim
    # stands. Recorded in scratch/ARTIFACTS.md items 1-6.

    def _claimed(self, fid):
        return {c["function_id"] for c in self.by_id[fid]["functions_claimed"]}

    def test_eld_absence_despite_driver_and_compliance_words(self):
        # ARTIFACTS item 5: "driver workflows, and regulatory
        # compliance" is present; no ELD / hours-of-service phrase
        # occurs; the vendor's ELD business elsewhere is not
        # evidence. The absence stands.
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertIn("driver workflows", desc, fid)
            self.assertIn("regulatory compliance", desc, fid)
            self.assertNotRegex(desc, r"(?i)electronic logging device|\beld\b|hours.of.service")
            self.assertNotIn("eld_integration", self._claimed(fid), fid)

    def test_reporting_absence_despite_reporting_word(self):
        # ARTIFACTS item 4: "reporting" appears in a four-item list
        # and "visibility" in sentence 1; the family's phrase
        # "reporting and analytics" occurs nowhere ("analytics"
        # occurs nowhere at all).
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertIn("reporting", desc, fid)
            self.assertIn("visibility", desc, fid)
            self.assertNotIn("analytics", desc.lower(), fid)
            self.assertNotIn("reporting and analytics", desc.lower(), fid)
            self.assertNotIn("reporting_analytics", self._claimed(fid), fid)

    def test_registry_and_search_absences(self):
        # ARTIFACTS items 1 and 6: no FMIS phrase (the registry
        # claim is the phrase itself) and no search vocabulary.
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertNotRegex(desc, r"(?i)fleet management information system|\bfmis\b")
            self.assertNotIn("vehicle_registry", self._claimed(fid), fid)
            self.assertNotRegex(desc, r"(?i)\bsearch\b")
            self.assertNotIn("search", self._claimed(fid), fid)

    def test_maintenance_absence_despite_monitoring(self):
        # ARTIFACTS item 3: "equipment monitoring" is present and is
        # not maintenance; no maintenance/inspection word occurs.
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertIn("equipment monitoring", desc, fid)
            self.assertNotRegex(desc, r"(?i)maintenance|inspection")
            self.assertNotIn("maintenance_inspection", self._claimed(fid), fid)

    def test_telematics_stands_on_its_own_phrase_only(self):
        # The telematics claim fires on the word "telematics"; the
        # family's other phrases (gps, live tracking, vehicle
        # location tracking) occur nowhere, and no claim was
        # manufactured from "real-time" or "visibility".
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertIn("fleet telematics", desc, fid)
            self.assertNotRegex(desc, r"(?i)\bgps\b|live tracking|vehicle location tracking")
            claim = [c for c in sheet["functions_claimed"]
                     if c["function_id"] == "telematics_gps"]
            self.assertEqual(len(claim), 1, fid)
            self.assertIn("fleet telematics", claim[0]["evidence"], fid)

    def test_no_control_language_anywhere(self):
        # Documented control claims: none. No description asserts an
        # access-control, authentication, encryption, or audit
        # phrase; nothing was filled in from a baseline.
        for fid, sheet in self.by_id.items():
            desc = sheet["description"].lower()
            for token in ("authorized users", "audit", "encrypt",
                          "access control", "authentication", "role-based"):
                self.assertNotIn(token, desc, f"{fid} {token}")
            self.assertNotIn("access_control", self._claimed(fid), fid)
            self.assertNotIn("audit_logging", self._claimed(fid), fid)


if __name__ == "__main__":
    unittest.main()
