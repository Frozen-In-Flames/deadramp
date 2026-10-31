"""Remainder additions — unit ``addition:grc-l2`` (see ADDENDUM.md).

Traces to: the 5 previously uncategorized forks appended to this
group's spec sheets by ``scratch/additions_extract.py`` — Anecdotes,
Halo, Kovr Nova, MediaLab Federal, Workiva Platform — spec'd under
the group's existing 14-family taxonomy applied verbatim.

Two halves:

- **Spec integrity.** Sheet count and unit order, membership against
  ``../../remainder.json``, the literal per-fork claim table,
  verbatim evidence, the zero-claim families pinned (not hidden),
  the near-miss pins (Halo's singular "Key Security Indicator",
  Kovr's "Authorization to Operate", MediaLab's "Role-based
  permissions" — none of them a taxonomy phrase), the wording
  artifact in Kovr's risk claim, and the retirement of the group's
  two named absences: ``risk_management`` and ``policy_management``
  are claimed by newcomers after standing at 0 of 2.
- **Substrate cases.** One case per addition fork against the
  unchanged core, exercising the records forms its claims
  presuppose: catalog registration for custom frameworks/policies
  (Anecdotes), the POA&M finding lifecycle with read-time overdue
  derivation (Halo), assessment + authorization records and an
  artifact evidence record (Kovr), a policy document held as an
  evidence record with reviewer-set validation status (MediaLab),
  and risk-assessment / issue / evidence-request records with a
  counts-only posture (Workiva). Posture is recursively asserted
  free of any score / rating / grade / percent key: the risk
  claims buy records verbatim, never a computed score.
"""

import json
import os
import re
import unittest

from grc.errors import PermissionDenied

import grc_helpers as H
from grc_helpers import ADMIN, MEMBER, SEED_FRAMEWORK_ID, SYSTEM_REF, make_store

_GROUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_ROOT = os.path.abspath(os.path.join(_GROUP_DIR, "..", ".."))
CATEGORY = "Governance, Risk, and Compliance (GRC)"
UNIT_ID = "addition:grc-l2"

ORIGINAL_IDS = ["FR2525557617", "FR2206159758"]
UNIT_IDS = [
    "FR2620235600",  # Anecdotes
    "FR2621445678",  # Halo
    "FR2607537684",  # Kovr.ai / Kovr Nova
    "FR2004146362",  # MediaLab, Inc. / MediaLab Federal
    "FR1726564822",  # Workiva / Workiva Platform
]

# The literal claim table the taxonomy produces for the additions,
# in taxonomy order per sheet. Pinned so any taxonomy drift — or
# any hand-edit of a sheet — fails the suite.
EXPECTED_CLAIMS = {
    "FR2620235600": [
        "continuous_monitoring",
        "control_framework_compliance",
        "posture_reporting",
        "policy_management",
    ],
    "FR2621445678": ["continuous_monitoring", "risk_management"],
    "FR2607537684": [
        "continuous_monitoring",
        "control_framework_compliance",
        "risk_management",
        "workflow_automation",
    ],
    "FR2004146362": ["policy_management"],
    "FR1726564822": ["risk_management", "api_integrations"],
}

# Families no addition claims, pinned rather than left implicit.
ZERO_CLAIM_FAMILIES = [
    "evidence_management",
    "ksi_tracking",
    "vulnerability_remediation",
    "assessment_authorization",
    "audit_support",
    "platform_hosting",
    "identity_access_hooks",
]


def load_sheets():
    with open(os.path.join(_GROUP_DIR, "specs", "specs.json")) as fh:
        return json.load(fh)


def addition_sheets():
    return {s["fork_id"]: s for s in load_sheets()[len(ORIGINAL_IDS):]}


def assert_no_score_keys(testcase, node):
    """Recursive posture discipline: no key anywhere mentions a
    score, rating, grade, or percent (mirrors test_posture.py)."""
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
        self.assertEqual(unit["extends_group"], "grc-l2")

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
            sum(len(v) for v in EXPECTED_CLAIMS.values()), 13
        )

    def test_sheet_fields_and_verbatim_evidence(self):
        for fid, sheet in addition_sheets().items():
            with self.subTest(fork=fid):
                self.assertEqual(sheet["deadramp_category"], CATEGORY)
                self.assertEqual(sheet["cmmc_tier"], "L2")
                self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
                self.assertTrue(sheet["description"])
                for claim in sheet["functions_claimed"]:
                    # Evidence is the fork's own sentence, verbatim.
                    self.assertIn(claim["evidence"], sheet["description"])

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
        self.assertEqual(checked, 8)

    def test_zero_claim_families_are_pinned(self):
        claimed = {
            c["function_id"]
            for s in addition_sheets().values()
            for c in s["functions_claimed"]
        }
        for family in ZERO_CLAIM_FAMILIES:
            with self.subTest(family=family):
                self.assertNotIn(family, claimed)

    def test_named_absences_retired_by_named_claimants(self):
        sheets = addition_sheets()

        def claimants(family):
            return {
                fid
                for fid, s in sheets.items()
                if family in [c["function_id"] for c in s["functions_claimed"]]
            }

        # risk_management stood at 0 of 2 in UNION-SPEC (named
        # absence); the additions claim it three times.
        self.assertEqual(
            claimants("risk_management"),
            {"FR2621445678", "FR2607537684", "FR1726564822"},
        )
        # policy_management likewise stood at 0 of 2; claimed twice.
        self.assertEqual(
            claimants("policy_management"),
            {"FR2620235600", "FR2004146362"},
        )

    def test_near_miss_pins(self):
        sheets = addition_sheets()
        halo = sheets["FR2621445678"]
        # Singular "Key Security Indicator validation" is not the
        # taxonomy's plural phrase, and no "KSI" token appears:
        # ksi_tracking does not fire, recorded as a near-miss.
        self.assertIn("Key Security Indicator validation", halo["description"])
        self.assertNotIn(
            "ksi_tracking", [c["function_id"] for c in halo["functions_claimed"]]
        )
        kovr = sheets["FR2607537684"]
        # Kovr writes "Authorization to Operate"; the taxonomy's
        # phrase is "Authority to Operate": no assessment claim.
        self.assertIn("Authorization to Operate", kovr["description"])
        self.assertNotIn(
            "assessment_authorization",
            [c["function_id"] for c in kovr["functions_claimed"]],
        )
        medialab = sheets["FR2004146362"]
        # "Role-based permissions" is not "role-based access
        # control": identity_access_hooks does not fire.
        self.assertIn("Role-based permissions", medialab["description"])
        self.assertNotIn(
            "identity_access_hooks",
            [c["function_id"] for c in medialab["functions_claimed"]],
        )

    def test_kovr_risk_claim_wording_artifact_stands(self):
        # Kovr's risk_management claim rests on the framework NAME
        # "DoD Risk Management Framework (RMF)" inside its
        # supported-frameworks list — the pattern is the taxonomy's
        # law and the claim stands, artifact recorded (ADDENDUM §2).
        kovr = addition_sheets()["FR2607537684"]
        risk = next(
            c for c in kovr["functions_claimed"]
            if c["function_id"] == "risk_management"
        )
        self.assertIn("Risk Management Framework", risk["evidence"])


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork against the unchanged
    core (Core functions per UNION-SPEC)."""

    def setUp(self):
        self.store, self.system, self.indicator = make_store()

    def test_anecdotes_custom_framework_and_policy_catalog(self):
        # Anecdotes "maps controls across 60+ industry frameworks
        # and custom policies": the catalog registry (Core 1) is
        # the records form — a custom framework and its controls
        # register as catalog records; monitoring results (Core 3)
        # record against them, posture stays counts-only.
        self.store.create_framework(
            "CUSTOM-POL-1", "Custom Policy Set", "1", actor=ADMIN,
            description="customer-defined policy framework",
        )
        control = self.store.create_control(
            "CUSTOM-POL-1", "GV-1", "Governance policy control", actor=ADMIN
        )
        self.assertEqual(control["family"], "GV")
        indicator = self.store.create_indicator(
            "KSI-CUST-1", "Custom policy coverage", ["GV-1"], actor=MEMBER
        )
        result = self.store.record_indicator_result(
            indicator["id"], SYSTEM_REF, "pass (as reported)", actor=MEMBER
        )
        self.assertEqual(result["status"], "pass (as reported)")
        posture = self.store.posture_summary(MEMBER)
        assert_no_score_keys(self, posture)

    def test_halo_poam_finding_lifecycle_and_derivation(self):
        # Halo's GRC module: "Plan of Action and Milestones (POA&M)
        # tracking" — finding records (Core 5), with overdue
        # derived at read, never stored.
        finding = H.make_finding(self.store, due_date="2026-06-30")
        on_due = self.store.get_finding(finding["id"], MEMBER, as_of="2026-06-30")
        self.assertEqual(on_due["derived_status"], "open")
        past = self.store.get_finding(finding["id"], MEMBER, as_of="2026-07-01")
        self.assertEqual(past["derived_status"], "overdue")
        stored = self.store.get_finding(finding["id"], MEMBER)
        self.assertNotIn("derived_status", stored)
        moved = self.store.transition_finding(
            finding["id"], "in_progress", actor=MEMBER
        )
        self.assertEqual(moved["status"], "in_progress")

    def test_kovr_assessment_authorization_and_artifact_evidence(self):
        # Kovr generates SSP/SAR/POA&M artifacts on the path to an
        # ATO: the records forms are assessment records and
        # authorization records (Core 6) and evidence records for
        # the artifacts themselves (Core 4).
        assessment = self.store.create_assessment(
            SYSTEM_REF, SEED_FRAMEWORK_ID, "full system, all controls",
            "assessor-3", "2026-09-15", "SAR issued (as reported)",
            actor=MEMBER,
        )
        self.assertEqual(assessment["result"], "SAR issued (as reported)")
        auth = self.store.create_authorization(
            SYSTEM_REF, SEED_FRAMEWORK_ID, actor=ADMIN
        )
        auth = self.store.transition_authorization(
            auth["id"], "in_progress", actor=ADMIN, note="readiness"
        )
        auth = self.store.transition_authorization(
            auth["id"], "authorized", actor=ADMIN, note="ATO granted"
        )
        self.assertEqual(auth["status"], "authorized")
        # History: creation step plus the two transitions.
        self.assertEqual(len(auth["history"]), 3)
        artifact = self.store.create_evidence(
            "System Security Plan (generated)",
            "ssp body as generated",
            ["IA-2"], [SYSTEM_REF], actor=MEMBER,
        )
        self.assertTrue(
            self.store.verify_evidence(
                artifact["id"], "ssp body as generated", actor=MEMBER
            )
        )
        self.assertFalse(
            self.store.verify_evidence(
                artifact["id"], "ssp body, edited", actor=MEMBER
            )
        )

    def test_medialab_policy_document_as_evidence_record(self):
        # MediaLab: "document management of policies and
        # procedures" — a policy document is an evidence record
        # (Core 4): metadata + SHA-256, validation status set by a
        # reviewer and recorded verbatim; the filer may not review.
        doc = self.store.create_evidence(
            "Policy POL-114: specimen handling",
            "policy body v3",
            ["IA-2"], [SYSTEM_REF], actor=MEMBER,
            description="policies and procedures document",
        )
        with self.assertRaises(PermissionDenied):
            self.store.review_evidence(
                doc["id"], "Approved (lab wording)", actor=MEMBER
            )
        reviewed = self.store.review_evidence(
            doc["id"], "Approved (lab wording)", actor=ADMIN
        )
        self.assertEqual(reviewed["validation_status"], "Approved (lab wording)")
        self.assertTrue(
            self.store.verify_evidence(doc["id"], "policy body v3", actor=MEMBER)
        )

    def test_workiva_risk_records_and_counts_only_posture(self):
        # Workiva: "Manage risk assessments, evidence requests,
        # issues, and findings with real-time reports and
        # dashboards" — assessment records (Core 6), finding
        # records (Core 5), evidence records (Core 4), posture
        # computed on read as counts only (Core 7): no score is
        # computed from any of it, anywhere.
        self.store.create_assessment(
            SYSTEM_REF, SEED_FRAMEWORK_ID, "annual risk assessment",
            "assessor-9", "2026-09-15", "risk assessment recorded",
            actor=MEMBER,
        )
        H.make_finding(self.store, title="Issue: stale access review")
        self.store.create_evidence(
            "Evidence request ER-1 response",
            "response body",
            ["IA-2"], [SYSTEM_REF], actor=MEMBER,
        )
        posture = self.store.posture_summary(MEMBER, as_of="2026-07-01")
        self.assertEqual(posture["findings"]["open"], 1)
        self.assertEqual(posture["findings"]["overdue"], 1)
        assert_no_score_keys(self, posture)


if __name__ == "__main__":
    unittest.main()
