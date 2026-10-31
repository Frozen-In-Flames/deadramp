"""Remainder additions — unit ``addition:human-resources-l2`` (see ADDENDUM.md).

Traces to: the 3 previously uncategorized forks appended to this
group's spec sheets by ``scratch/additions_extract.py`` — GDC
Integration General Support System (GSS), Government Retirement &
Benefits GRB Platform, Perceptyx Insights Platform — spec'd under
the group's existing 25-family taxonomy applied verbatim (proven by
the extractor's exact reproduction of the original 4 claim tables).

Two halves:

- **Spec integrity.** Sheet count and unit order, membership against
  ``../../remainder.json``, the literal per-fork claim table,
  verbatim evidence, the zero-claim families pinned (not hidden),
  the near-miss pins (GDC's "Labor-Employee Relations" is not the
  contiguous phrase "labor relations"; "role management" is not
  "role-based"; GRB's "interface" is not ``integrat\\w+``;
  Perceptyx's "performance improvement" is not "performance
  management"), the wording artifacts that stand (GDC's benefits
  claim on the generic phrase "benefits of single sign on"; its
  awards claim first-matched on "awards laws"), and the absence
  updates: the leave named absence is retired by GDC's Paycheck 8
  prose, time & attendance is retired by substance though its
  literal probe pattern does not fire on the comma wording, and
  payroll now appears once — as GRB's external-system interface
  reference, not as a function.
- **Substrate cases.** One case per addition fork against the
  unchanged core, exercising the records forms its claims
  presuppose: an onboarding lifecycle case derived to complete,
  a performance cycle, and personnel-action / award /
  labor-relations case records (GDC); retirement and benefits
  records with employee scope (GRB); counts-only reporting over
  the records with no computed score anywhere (Perceptyx).
  Person records stay opaque-reference only throughout.
"""

import json
import os
import re
import unittest

from hr.errors import PermissionDenied

import hr_helpers as H
from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store

_GROUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ROOT = os.path.abspath(os.path.join(_GROUP_DIR, "..", ".."))
CATEGORY = "Human Resources"
UNIT_ID = "addition:human-resources-l2"

ORIGINAL_IDS = ["FR1711546389", "FR2410056366", "F1301251880", "FR2016962740"]
UNIT_IDS = [
    "FR1834348080",  # GDC Integration, Inc. / General Support System (GSS)
    "FR2002757173",  # Government Retirement & Benefits, Inc. / GRB Platform
    "FR1818240234",  # Perceptyx / Perceptyx Insights Platform
]

# The literal claim table the taxonomy produces for the additions,
# in taxonomy order per sheet. Pinned so any taxonomy drift — or
# any hand-edit of a sheet — fails the suite.
EXPECTED_CLAIMS = {
    "FR1834348080": [
        "onboarding",
        "performance_management",
        "benefits_retirement",
        "personnel_actions_cases",
        "awards_recognition",
        "workforce_planning",
        "ai_automation",
        "reporting_analytics",
        "audit_compliance",
    ],
    "FR2002757173": ["benefits_retirement"],
    "FR1818240234": ["reporting_analytics"],
}

# Families no addition claims, pinned rather than left implicit.
ZERO_CLAIM_FAMILIES = [
    "talent_acquisition",
    "applicant_tracking",
    "vacancy_announcements",
    "position_classification",
    "job_analysis",
    "hiring_assessments",
    "panel_review",
    "referral_certificates",
    "separation",
    "labor_relations",
    "talent_management",
    "talent_mobility",
    "recruiting_outreach",
    "learning_upskilling",
    "integrations",
    "access_control",
]

# The six named-absence probes from UNION-SPEC, re-run in-test.
ABSENCE_PROBES = {
    "leave_time_off": r"(leave|time off|paid time off|vacation)",
    "policy_acknowledgements": r"(polic|acknowledg)",
    "payroll": r"(payroll)",
    "background_checks": r"(background check|background investigation)",
    "salary_compensation": r"(salary|compensation)",
    "time_attendance": r"(time and attendance|timesheet)",
}


def load_sheets():
    with open(os.path.join(_GROUP_DIR, "specs", "specs.json")) as fh:
        return json.load(fh)


def addition_sheets():
    return {s["fork_id"]: s for s in load_sheets()[len(ORIGINAL_IDS):]}


def assert_no_score_keys(testcase, node):
    """Recursive reporting discipline: no key anywhere mentions a
    score, rating, grade, or percent — reporting is counts only."""
    if isinstance(node, dict):
        for key, value in node.items():
            lowered = str(key).lower()
            testcase.assertNotIn("score", lowered)
            testcase.assertNotIn("rating", lowered)
            testcase.assertNotIn("grade", lowered)
            testcase.assertNotIn("percent", lowered)
            assert_no_score_keys(testcase, value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            assert_no_score_keys(testcase, value)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """The appended sheets are exactly the census unit, tagged by
    the group's taxonomy verbatim."""

    def test_sheet_count_and_unit_order(self):
        sheets = load_sheets()
        self.assertEqual(len(sheets), 7)
        self.assertEqual(
            [s["fork_id"] for s in sheets], ORIGINAL_IDS + UNIT_IDS
        )

    def test_membership_matches_remainder_unit(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        unit = next(
            u for u in remainder["build_units"] if u["unit_id"] == UNIT_ID
        )
        self.assertEqual(unit["fork_ids"], UNIT_IDS)
        self.assertEqual(unit["category"], CATEGORY)
        self.assertEqual(unit["tier"], "L2")
        self.assertEqual(unit["extends_group"], "human-resources-l2")

    def test_per_fork_claim_table_is_literal(self):
        sheets = addition_sheets()
        self.assertEqual(set(sheets), set(UNIT_IDS))
        for fid, expected in EXPECTED_CLAIMS.items():
            with self.subTest(fork=fid):
                self.assertEqual(
                    [c["function_id"] for c in sheets[fid]["functions_claimed"]],
                    expected,
                )
        self.assertEqual(
            sum(len(v) for v in EXPECTED_CLAIMS.values()), 11
        )

    def test_sheet_fields_and_verbatim_evidence(self):
        for fid, sheet in addition_sheets().items():
            with self.subTest(fork=fid):
                self.assertEqual(sheet["deadramp_category"], CATEGORY)
                self.assertEqual(sheet["cmmc_tier"], "L2")
                self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
                self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
                self.assertTrue(sheet["description"])
                for claim in sheet["functions_claimed"]:
                    # Evidence is the fork's own sentence, verbatim
                    # (or its 400-char truncation, per house method):
                    # either way the stored text is a substring of
                    # the fork's own description, under the house
                    # splitter's own \r -> space normalization (the
                    # raw GDC text carries \r\n line endings).
                    ev = claim["evidence"]
                    core = ev[:-3] if ev.endswith("...") else ev
                    self.assertIn(core, sheet["description"].replace("\r", " "))

    def test_census_citations_verify_against_descriptions(self):
        with open(os.path.join(_ROOT, "remainder.json")) as fh:
            remainder = json.load(fh)
        census = {e["fork_id"]: e for e in remainder["forks"]}
        sheets = addition_sheets()
        checked = 0
        for fid in UNIT_IDS:
            desc = sheets[fid]["description"]
            normalized = re.sub(r"\s+", " ", desc)
            for cite in census[fid].get("citations", []):
                text = cite if isinstance(cite, str) else cite.get("sentence", "")
                self.assertTrue(
                    text in desc or re.sub(r"\s+", " ", text) in normalized,
                    (fid, text),
                )
                checked += 1
        self.assertEqual(checked, 3)

    def test_zero_claim_families_are_pinned(self):
        claimed = {
            c["function_id"]
            for s in addition_sheets().values()
            for c in s["functions_claimed"]
        }
        for family in ZERO_CLAIM_FAMILIES:
            with self.subTest(family=family):
                self.assertNotIn(family, claimed)

    def test_near_miss_pins(self):
        sheets = addition_sheets()
        gdc = sheets["FR1834348080"]
        gdc_ids = [c["function_id"] for c in gdc["functions_claimed"]]
        # LERIS is literally a labor-relations system, but the text
        # writes "Labor-Employee Relations" / "labor/employee
        # relations" — never the taxonomy's contiguous phrase
        # "labor relations": the family does not fire.
        self.assertIn(
            "Labor-Employee Relations Information System", gdc["description"]
        )
        self.assertNotIn("labor relations", gdc["description"].lower())
        self.assertNotIn("labor_relations", gdc_ids)
        # "role management" is not "role-based" / "access control" /
        # "granted access": access_control does not fire.
        self.assertIn("role management", gdc["description"])
        self.assertNotIn("role-based", gdc["description"].lower())
        self.assertNotIn("access_control", gdc_ids)
        # The vendor's NAME contains "Integration"; the description
        # body contains no integrat\w+ token: integrations does not
        # fire on a name.
        self.assertNotIn("integrat", gdc["description"].lower())
        self.assertNotIn("integrations", gdc_ids)

        grb = sheets["FR2002757173"]
        # GRB's "flexible bi-directional interface" is not an
        # integrat\w+ token: integrations does not fire.
        self.assertIn("bi-directional interface", grb["description"])
        self.assertNotIn("integrat", grb["description"].lower())
        self.assertNotIn(
            "integrations",
            [c["function_id"] for c in grb["functions_claimed"]],
        )

        perceptyx = sheets["FR1818240234"]
        # "performance improvement services" is not "performance
        # management": the family does not fire — Perceptyx's survey
        # function has no taxonomy family at all (see ADDENDUM §5).
        self.assertIn("performance improvement", perceptyx["description"])
        self.assertNotIn(
            "performance management", perceptyx["description"].lower()
        )
        self.assertNotIn(
            "performance_management",
            [c["function_id"] for c in perceptyx["functions_claimed"]],
        )

    def test_wording_artifacts_stand(self):
        gdc = addition_sheets()["FR1834348080"]
        claims = {c["function_id"]: c for c in gdc["functions_claimed"]}
        # benefits_retirement fires on the GENERIC phrase "benefits
        # of single sign on" in the Connect HR sentence — no benefits
        # administration is asserted there. The claim stands at
        # artifact weight; the family's substantive second claimant
        # is GRB (ADDENDUM §2).
        self.assertIn("benefits of single sign on", claims["benefits_retirement"]["evidence"])
        # awards_recognition first-matches the ePM sentence's
        # "awards laws"; the substantive awards surface (eTracker's
        # "Awards Processing") sits later in the same description.
        self.assertIn("awards laws", claims["awards_recognition"]["evidence"])
        self.assertIn("Awards Processing", gdc["description"])
        # ai_automation fires via automat\w+ on FedChart's
        # "automates the creation" — automation with NO AI wording
        # anywhere in the description (the UNION-SPEC caveat-3
        # precedent, FedHire's onboarding automation).
        self.assertIn("automates the creation", claims["ai_automation"]["evidence"])
        self.assertNotIn("artificial intelligence", gdc["description"].lower())
        self.assertIsNone(re.search(r"\bAI\b", gdc["description"], re.I))
        # audit_compliance fires on the compliance-OUTCOME phrase
        # "maintaining compliance with performance and awards laws";
        # no "audit" token appears in the evidence sentence (the
        # UNION-SPEC caveat-5 precedent, Eightfold).
        self.assertIn(
            "maintaining compliance", claims["audit_compliance"]["evidence"]
        )
        self.assertNotIn("audit", claims["audit_compliance"]["evidence"].lower())

    def test_absence_updates_are_pinned(self):
        sheets = addition_sheets()

        def probe_hits(fid, probe):
            return re.findall(
                ABSENCE_PROBES[probe], sheets[fid]["description"], re.I
            )

        # Leave & time-off: RETIRED by GDC's Paycheck 8 prose
        # ("leave (including VLTP and FLMA)", "Leave balances").
        self.assertTrue(probe_hits("FR1834348080", "leave_time_off"))
        # Time & attendance: the literal probe ("time and
        # attendance") does NOT fire — GDC writes "time, attendance"
        # with a comma — yet the Paycheck 8 substance is exactly
        # time, attendance & leave. Both facts pinned; the absence
        # is retired by substance (ADDENDUM §3).
        self.assertFalse(probe_hits("FR1834348080", "time_attendance"))
        self.assertIn("time, attendance", sheets["FR1834348080"]["description"].lower())
        # Payroll: the word now appears exactly once across the
        # enlarged group — inside GRB's interface sentence, naming
        # an EXTERNAL system it communicates with. No fork claims a
        # payroll function; the absence stands as a function.
        self.assertEqual(len(probe_hits("FR2002757173", "payroll")), 1)
        self.assertIn("payroll/HRIS", sheets["FR2002757173"]["description"])
        # The remaining three absences still hold across all three
        # newcomers (and so across all 7 forks).
        for probe in ("policy_acknowledgements", "background_checks",
                      "salary_compensation"):
            for fid in UNIT_IDS:
                with self.subTest(probe=probe, fork=fid):
                    self.assertFalse(probe_hits(fid, probe))


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork against the unchanged
    core (Core functions per UNION-SPEC)."""

    def test_gdc_onboarding_performance_and_case_records(self):
        # GDC GSS claims onboarding (eForms new-hire enrollment),
        # performance_management (ePM appraisal process), and
        # personnel_actions_cases (LERIS case management; eTracker
        # SF-52/SF-50 and awards processing). The records forms:
        # lifecycle cases with task checklists and read-derived
        # status (Core 6), performance review cycles (Core 7),
        # personnel case records (Core 9).
        store, _, _ = make_store()
        case = store.create_lifecycle_case(
            "carol", "onboarding", SPECIALIST,
            task_titles=["Enrollment forms", "Enrollment procedures"],
        )
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        view = store.get_lifecycle_case(case["id"], ADMIN)
        self.assertEqual(view["status"], "in_progress")
        store.set_task_state(case["id"], "t-2", "done", SPECIALIST)
        view = store.get_lifecycle_case(case["id"], ADMIN)
        self.assertEqual(view["status"], "complete")
        self.assertTrue(view["complete"])

        review = store.create_performance_review(
            "carol", "FY2026 appraisal", SPECIALIST,
            period_start="2025-10-01", period_end="2026-09-30",
        )
        store.set_review_state(review["id"], "in_progress", SPECIALIST)
        done = store.set_review_state(
            review["id"], "completed", SPECIALIST,
            outcome="appraisal recorded (verbatim label)",
        )
        self.assertEqual(done["outcome"], "appraisal recorded (verbatim label)")

        # Core 9 kinds carry the case substance: a personnel action
        # (eTracker's SF-52), an award (eTracker's awards
        # processing), and a labor_relations case (LERIS's domain —
        # the kind itself traces to Econ's original claim; GDC's
        # family claim is personnel_actions_cases, pinned above).
        for kind, title in (
            ("personnel_action", "SF-52 Request for Personnel Action"),
            ("award", "Awards Processing"),
            ("labor_relations", "LERIS case"),
        ):
            rec = store.create_case("carol", kind, title, SPECIALIST)
            self.assertEqual(rec["kind"], kind)
            self.assertEqual(rec["state"], "opened")
        report = store.report(ADMIN)
        self.assertEqual(report["cases"], 3)
        self.assertEqual(report["lifecycle_cases_by_status"]["complete"], 1)
        self.assertEqual(report["performance_reviews_by_state"]["completed"], 1)

    def test_grb_retirement_and_benefits_records(self):
        # GRB Platform is the substantive second claimant of the
        # group's thinnest Core family, benefits_retirement (was
        # 1 of 4, flagged thin): a complete federal retirement &
        # benefits administration product. The records form is
        # Core 8 — enrollment and retirement-case records keyed by
        # opaque plan_ref; no benefit amount is computed anywhere.
        store, _, _ = make_store()
        retirement = store.create_benefits_record(
            "carol", "retirement_case", "grb-retirement", SPECIALIST
        )
        self.assertEqual(retirement["state"], "pending")
        active = store.set_benefits_state(retirement["id"], "active", SPECIALIST)
        self.assertEqual(active["state"], "active")
        enrollment = store.create_benefits_record(
            "carol", "benefit_enrollment", "grb-benefits", SPECIALIST
        )
        store.set_benefits_state(enrollment["id"], "active", SPECIALIST)
        # Employee scope (Core 11): carol reads her own record; she
        # may not create records.
        own = store.get_benefits_record(retirement["id"], EMPLOYEE)
        self.assertEqual(own["id"], retirement["id"])
        with self.assertRaises(PermissionDenied):
            store.create_benefits_record(
                "carol", "benefit_enrollment", "x", EMPLOYEE
            )
        report = store.report(ADMIN)
        self.assertEqual(report["benefits_records"], 2)
        self.assertEqual(report["benefits_records_by_state"]["active"], 2)

    def test_perceptyx_reporting_is_counts_only(self):
        # Perceptyx's one claim is reporting_analytics (diagnostic
        # reporting module): the records form is Core 10 — counts
        # and breakdowns over the substrate records. Its survey
        # scores, benchmarks, and engagement indices are engines
        # (ADDENDUM §5): no score-shaped key exists anywhere in the
        # report, and an employee may not read it.
        store, _, _ = make_store()
        case = store.create_lifecycle_case(
            "carol", "onboarding", SPECIALIST, task_titles=["Survey follow-up"]
        )
        store.set_task_state(case["id"], "t-1", "done", SPECIALIST)
        store.create_performance_review("carol", "FY2026", SPECIALIST)
        store.create_case("carol", "general", "Action planning follow-up", SPECIALIST)
        report = store.report(ADMIN)
        self.assertEqual(report["persons"], 1)
        self.assertEqual(report["lifecycle_cases"], 1)
        self.assertEqual(report["lifecycle_cases_by_status"]["complete"], 1)
        self.assertEqual(report["performance_reviews"], 1)
        self.assertEqual(report["cases"], 1)
        assert_no_score_keys(self, report)
        with self.assertRaises(PermissionDenied):
            store.report(EMPLOYEE)


if __name__ == "__main__":
    unittest.main()
