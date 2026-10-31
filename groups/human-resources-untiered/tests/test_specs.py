"""Spec-sheet pins for the Human Resources untiered set (Untiered Set 16).

Traces to: UNION-SPEC.md (this group) — census membership, tier
discipline, and the literal claim table. These tests pin the
specs, not the code: exactly 2 sheets, membership exact against
census unit ``untiered:Human Resources`` in ../../../remainder.json,
every sheet recording the source's impact level as-is ("Unknown")
with ``cmmc_tier`` null, every description equal to the census's
recorded description for the fork, every claim's evidence verbatim
in its fork's description, and the literal result of the verbatim
taxonomy application — **6 claims across the set (Dayforce 5:
benefits_retirement, reporting_analytics, audit_compliance,
integrations, access_control; Replicon 1: ai_automation at
automation weight); no zero-claim fork; 19 of 25 families at
zero** — so a future re-extraction that quietly re-tunes the
taxonomy, or a sheet edit that manufactures a claim, fails here
instead of drifting. The absence pins hold this set's
adjudications (scratch/ARTIFACTS.md): the founding six named
absences re-probed on THESE forks' words — leave & time-off,
policy acknowledgements, background checks, and salary /
compensation stand here; payroll and time & attendance stand in
substance with no taxonomy family, as gaps, not claims. The
tiered-L2 retirements of leave and time & attendance do not
transfer to this set; each set is adjudicated on its own words.
"""

import json
import os
import re
import unittest

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

UNIT_ID = "untiered:Human Resources"
DAYFORCE = "FR2633957417"
REPLICON = "F1606087903"
EXPECTED_CLAIMS = {
    DAYFORCE: ["benefits_retirement", "reporting_analytics",
               "audit_compliance", "integrations", "access_control"],
    REPLICON: ["ai_automation"],
}
ALL_FAMILIES = [
    "talent_acquisition", "applicant_tracking", "vacancy_announcements",
    "position_classification", "job_analysis", "hiring_assessments",
    "panel_review", "referral_certificates", "onboarding",
    "performance_management", "benefits_retirement",
    "personnel_actions_cases", "separation", "labor_relations",
    "awards_recognition", "workforce_planning", "talent_management",
    "talent_mobility", "recruiting_outreach", "learning_upskilling",
    "ai_automation", "reporting_analytics", "audit_compliance",
    "integrations", "access_control",
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
        cls.uncovered = {
            u["fork_id"]: u
            for u in _load(os.path.join(_ROOT, "remainder", "uncovered.json"))
        }
        forks = _load(os.path.join(_ROOT, "forks.json"))
        rows = forks if isinstance(forks, list) else forks.get("forks", forks)
        cls.registry = {
            r["source_url"].rstrip("/").split("/")[-1]: r for r in rows
        }

    def _claimed(self, fid):
        return {c["function_id"] for c in self.by_id[fid]["functions_claimed"]}

    def test_exactly_two_sheets(self):
        self.assertEqual(len(self.specs), 2)

    def test_membership_exact_against_census_unit(self):
        self.assertEqual([s["fork_id"] for s in self.specs], self.unit_ids)
        self.assertEqual(self.unit_ids, [DAYFORCE, REPLICON])
        self.assertEqual(set(self.by_id), set(self.unit_ids))

    def test_tier_discipline_on_every_sheet(self):
        for sheet in self.specs:
            self.assertEqual(sheet["fedramp_impact_level"], "Unknown",
                             sheet["fork_id"])
            self.assertIsNone(sheet["cmmc_tier"], sheet["fork_id"])
            self.assertEqual(sheet["deadramp_category"], "Human Resources",
                             sheet["fork_id"])

    def test_registry_fields_match_forks_json(self):
        for fid, sheet in self.by_id.items():
            reg = self.registry[fid]
            self.assertEqual(sheet["vendor"], reg["vendor"], fid)
            self.assertEqual(sheet["product"], reg["product"], fid)
            self.assertEqual(sheet["authorization_status"],
                             reg["authorization_status"], fid)
            self.assertEqual(sheet["source_url"], reg["source_url"], fid)
        # As filed, the set is mixed: Dayforce is filed Analytics in
        # forks.json, Replicon Uncategorized; the census assignment
        # to Human Resources is the census's, recorded on the sheets.
        self.assertEqual(self.registry[DAYFORCE]["category"], "Analytics")
        self.assertEqual(self.registry[REPLICON]["category"],
                         "Uncategorized (none in source)")

    def test_recorded_fields_as_in_source(self):
        d = self.by_id[DAYFORCE]
        self.assertEqual(d["authorization_status"], "Initial Implementation")
        self.assertEqual(d["deployment_model"], "Government Community Cloud")
        self.assertEqual(d["service_model"], ["SaaS"])
        self.assertEqual(d["business_categories_in_source"],
                         ["Analytics", "Finance", "Human Resources"])
        r = self.by_id[REPLICON]
        self.assertEqual(r["authorization_status"], "FedRAMP In Process")
        self.assertEqual(r["deployment_model"], "Public Cloud")
        self.assertEqual(r["service_model"], ["SaaS"])
        self.assertEqual(r["business_categories_in_source"], [])

    def test_descriptions_match_census_record(self):
        for fid, sheet in self.by_id.items():
            self.assertEqual(sheet["description"],
                             self.uncovered[fid]["description"].strip(), fid)

    def test_literal_claim_table(self):
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"] for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 6)

    def test_no_zero_claim_forks(self):
        zero = {s["fork_id"] for s in self.specs if not s["functions_claimed"]}
        self.assertEqual(zero, set())

    def test_nineteen_families_at_zero(self):
        claimed = set()
        for s in self.specs:
            claimed |= {c["function_id"] for c in s["functions_claimed"]}
        self.assertEqual(claimed,
                         {"benefits_retirement", "reporting_analytics",
                          "audit_compliance", "integrations", "access_control",
                          "ai_automation"})
        self.assertEqual(len(set(ALL_FAMILIES) - claimed), 19)

    def test_every_evidence_verbatim_in_description(self):
        for sheet in self.specs:
            # Founding normalization: carriage returns become spaces
            # before sentence-splitting, so evidence is checked
            # against the normalized description.
            norm = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], norm,
                              f"{sheet['fork_id']} {claim['function_id']}")

    # -- Adjudication pins (scratch/ARTIFACTS.md).

    def test_replicon_ai_claim_is_automation_weight_only(self):
        # ARTIFACTS item 2: the claim rests on "automating"; the
        # description contains no AI wording at all (the FedHire
        # caveat-3 precedent). Automation is claimed; AI is not
        # asserted by this fork.
        desc = self.by_id[REPLICON]["description"]
        self.assertNotRegex(desc, r"(?i)\bAI\b|artificial intelligence")
        claim = [c for c in self.by_id[REPLICON]["functions_claimed"]
                 if c["function_id"] == "ai_automation"]
        self.assertEqual(len(claim), 1)
        self.assertIn("automating", claim[0]["evidence"])

    def test_workforce_management_is_not_performance_or_planning(self):
        # ARTIFACTS item 3: Dayforce's capability list names
        # "workforce management" — neither the performance_management
        # phrase nor workforce_planning / resource management.
        desc = self.by_id[DAYFORCE]["description"]
        self.assertIn("workforce management", desc)
        self.assertNotIn("performance management", desc.lower())
        self.assertNotIn("workforce planning", desc.lower())
        self.assertNotIn("resource management", desc.lower())
        self.assertNotIn("performance_management", self._claimed(DAYFORCE))
        self.assertNotIn("workforce_planning", self._claimed(DAYFORCE))

    def test_hiring_chain_entirely_absent(self):
        chain = {"talent_acquisition", "applicant_tracking",
                 "vacancy_announcements", "position_classification",
                 "job_analysis", "hiring_assessments", "panel_review",
                 "referral_certificates", "onboarding", "separation"}
        for fid in self.by_id:
            self.assertFalse(chain & self._claimed(fid), fid)

    def test_leave_absence_stands_in_this_set(self):
        # The tiered-L2 retirement (an addition fork's Paycheck 8
        # prose) does not transfer: neither description here
        # contains leave wording. Adjudicated on these words.
        for fid, sheet in self.by_id.items():
            self.assertNotRegex(
                sheet["description"],
                r"(?i)leave|time off|paid time off|vacation", fid)

    def test_policy_background_salary_absences_stand(self):
        for fid, sheet in self.by_id.items():
            desc = sheet["description"]
            self.assertNotRegex(desc, r"(?i)polic|acknowledg", fid)
            self.assertNotRegex(
                desc, r"(?i)background check|background investigation", fid)
            self.assertNotRegex(desc, r"(?i)salary|compensation", fid)

    def test_payroll_substance_present_but_no_family(self):
        # Dayforce names payroll among its OWN capabilities (not an
        # external-system reference). No taxonomy family exists for
        # payroll: it is a gap in this set, not a claim, and the
        # founding absence does not stand here.
        desc = self.by_id[DAYFORCE]["description"]
        self.assertIn("payroll", desc)
        self.assertNotIn("payroll", self._claimed(DAYFORCE))
        self.assertNotIn("payroll", self.by_id[REPLICON]["description"])

    def test_time_attendance_substance_present_but_no_family(self):
        # Replicon's whole function is time tracking and the
        # founding probe word "timesheet" occurs literally. No
        # taxonomy family exists for time & attendance: gap, not
        # claim. (The tiered retirement reached the same substance
        # conclusion on different words; here the probe itself
        # fires.)
        desc = self.by_id[REPLICON]["description"]
        self.assertIn("timesheet", desc)
        self.assertIn("time tracking", desc)
        self.assertNotIn("time_attendance", self._claimed(REPLICON))

    def test_dayforce_moderate_prose_moves_no_tier(self):
        # Dayforce's prose asserts a "FedRAMP Moderate
        # authorization" and "Federal Moderate impact
        # information"; its own record says impact Unknown and
        # status Initial Implementation. The assertion is the
        # fork's claim about itself, recorded; the tier stays null.
        sheet = self.by_id[DAYFORCE]
        self.assertIn("FedRAMP Moderate authorization", sheet["description"])
        self.assertIn("Federal Moderate impact information",
                      sheet["description"])
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertEqual(sheet["authorization_status"],
                         "Initial Implementation")
        self.assertIsNone(sheet["cmmc_tier"])

    def test_documented_control_phrases_present_in_dayforce_only(self):
        # Documented control claims trace to Dayforce's security
        # sentences; Replicon's description carries no control
        # language in any form.
        d = self.by_id[DAYFORCE]["description"]
        for phrase in ("role-based access control",
                       "privileged access management",
                       "centralized audit logging",
                       "multifactor authentication",
                       "identity federation",
                       "FIPS 140-3 validated cryptographic modules",
                       "continuous monitoring", "incident response",
                       "vulnerability management"):
            self.assertIn(phrase, d, phrase)
        r = self.by_id[REPLICON]["description"].lower()
        for token in ("audit", "role-based", "authentication",
                      "encryption", "access control", "monitoring"):
            self.assertNotIn(token, r, token)


if __name__ == "__main__":
    unittest.main()
