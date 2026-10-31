"""Remainder addition (unit addition:education-training-l2): spec
integrity and substrate cases for the 1 addition fork.

Traces to: ADDENDUM.md for Group 13 (Education & Training,
CMMC L2). The previously uncategorized fork (Pearson VUE /
Pearson Federal Cloud System) was spec'd under the group's
EXISTING 21-family taxonomy applied verbatim — the additions
extractor parses the TAXONOMY literal out of the shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed) and reproduces the original 8 forks' shipped claim
tables exactly (whole sheets deep-equal; 43 claims) before
tagging the newcomer. The original extractor carries no
CORRECTIONS literal: its six wording-artifact corrections were
applied by tightening the patterns themselves
(``scratch/ARTIFACTS.md``), so the shipped patterns are the
corrected taxonomy.

The newcomer claims **4 families**, all Core, all substantive:
``enrollment_registration`` and ``assessments`` (sentence 1:
"delivers assessments to registered testing candidates"),
``scheduling`` and ``reporting_analytics`` (sentence 3: its own
FedRAMP-boundary enumeration of its own registration/scheduling
and reporting systems). The group total moves 43 -> 47, and the
union spec's floor — no fork has zero claims — **survives**:
9 of 9 forks claim. Neither claim extends the core: all four
families are already Core functions 2, 4, 7, and 8, and ``src/``
is byte-identical.

Two honesty findings are pinned, not smoothed over. (1) The
census twist: of the fork's 2 census citations, citation 1
verifies as a strict verbatim substring and is itself the
enrollment/assessments evidence sentence, while citation 2
verifies only whitespace-normalized — the source text carries a
line break inside that sentence ("assessments\\n to"). Neither
citation is load-bearing; every claim rests on the description
itself. (2) The proctoring substance change: the union spec
records proctoring as a named absence (0/8), but the newcomer's
own words name "the OnVUE online proctoring platform". No
taxonomy family exists for proctoring, so no claim fires; the
already-registered gap (README gap 5, Remote proctoring &
identity proofing) gains a claimant in substance for the
proctoring half only — the description contains no identity
token, so identity proofing remains absent in both senses.

The substrate cases exercise the shipped core as the newcomer
would use it: an assessment program in the registry (Core 1), a
candidate registration (Core 2), a scheduled candidate test
session (Core 7), an assessment administration record holding a
verbatim response and no score field (Core 4), reporting over
those records (Core 8), and a compliance assignment whose past-
due status is derived at read (Core 6 — that assertion trips
the group's signature ``_derive_status`` drill by exactly one;
see tests/README.md). The delivery/test-driver engine, the
OnVUE proctoring engine, and the IntelliVUE reporting engine
themselves are Extended (ADDENDUM section 5), not implemented,
and nothing in these cases claims them.
"""

import json
import os
import re
import unittest

from learn_helpers import ADMIN, INSTRUCTOR, fresh_store, make_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "F1506076709",   # Blackboard — Blackboard LMS
    "FR1707156421",  # Envisage Technologies LLC — Acadis Readiness Suite
    "FR2422436886",  # Laerdal Labs D.C. — SimCapture Cloud Government
    "FR2119265538",  # NEOGOV — NEOGOV Cloud
    "FR2326160742",  # PDRI by Pearson — Palladium
    "FR2607643783",  # PSI Services LLC — Gov Secure Cloud
    "FR2609449664",  # Pepelwerk LLC — Pepelwerk Government
    "FR1716961549",  # Peraton Corporation — Next Generation Cloud Platform
]
UNIT_ORDER = [
    "FR2135637226",  # Pearson VUE — Pearson Federal Cloud System
]

ORIGINAL_CLAIM_COUNTS = {
    "F1506076709": 3,
    "FR1707156421": 7,
    "FR2422436886": 4,
    "FR2119265538": 5,
    "FR2326160742": 3,
    "FR2607643783": 8,
    "FR2609449664": 11,
    "FR1716961549": 2,
}

# The literal claim table for the addition, in taxonomy order.
EXPECTED_CLAIMS = {
    "FR2135637226": [
        "enrollment_registration",
        "assessments",
        "scheduling",
        "reporting_analytics",
    ],
}

_S1 = (
    "Pearson VUEs Pearson Federal Cloud System securely delivers "
    "assessments to registered testing candidates for over 450 "
    "assessment programs."
)
_S3 = (
    "The system is built on Microsoft\u2019s Azure Commercial Cloud "
    "infrastructure-as-a-service (IaaS)\n\n\nPearson VUE\u2019s FedRAMP "
    "boundary includes candidate registration and scheduling systems; "
    "candidate testing on Athena Browser Edition (A-BE) or Athena "
    "Desktop (A-DE) test drivers; the OnVUE online proctoring "
    "platform; and reporting systems, including IntelliVUE."
)
EXPECTED_EVIDENCE = {
    "enrollment_registration": _S1,
    "assessments": _S1,
    "scheduling": _S3,
    "reporting_analytics": _S3,
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


def _raw_product(fork_id):
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in prods}[fork_id]


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM sections 1/2: membership, order, literal claim
    table, verbatim description and evidence, census citation
    accounting, near-miss pins, absence accounting."""

    def test_sheet_count_and_order(self):
        """9 sheets: the 8 shipped originals untouched in place,
        then the addition in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheet is exactly the census unit's fork,
        extending exactly this group."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:education-training-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "education-training-l2")
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[8:]],
                         unit["fork_ids"])

    def test_original_claim_tables_stand(self):
        """The original 8 forks' shipped claim tables stand
        exactly (43 claims in the shipped per-fork counts)."""
        specs = _load_specs()
        for fork_id, count in ORIGINAL_CLAIM_COUNTS.items():
            self.assertEqual(
                len(_sheet(specs, fork_id)["functions_claimed"]), count,
                fork_id)
        self.assertEqual(
            sum(len(_sheet(specs, f)["functions_claimed"])
                for f in ORIGINAL_ORDER), 43)

    def test_literal_claim_table(self):
        """The addition fork claims exactly the 4 pinned
        families, in taxonomy order, with the pinned evidence
        sentences."""
        specs = _load_specs()
        sheet = _sheet(specs, "FR2135637226")
        got = [c["function_id"] for c in sheet["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS["FR2135637226"])
        for claim in sheet["functions_claimed"]:
            self.assertEqual(claim["evidence"],
                             EXPECTED_EVIDENCE[claim["function_id"]])

    def test_group_totals(self):
        """The group total moves 43 -> 47 claims. The union
        spec's floor survives the addition: no fork — original
        or newcomer — has zero claims (9 of 9 claim). Family
        counts for the four claimed families move to
        enrollment_registration 3, assessments 3, scheduling 3,
        reporting_analytics 4 (forks claiming, of 9)."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 47)
        zero = [s["fork_id"] for s in specs if not s["functions_claimed"]]
        self.assertEqual(zero, [])
        by_family = {}
        for s in specs:
            for c in s["functions_claimed"]:
                by_family.setdefault(c["function_id"], []).append(s["fork_id"])
        self.assertEqual(len(by_family["enrollment_registration"]), 3)
        self.assertEqual(len(by_family["assessments"]), 3)
        self.assertEqual(len(by_family["scheduling"]), 3)
        self.assertEqual(len(by_family["reporting_analytics"]), 4)
        self.assertIn("FR2135637226", by_family["assessments"])

    def test_addition_tier_fields(self):
        """The addition is FedRAMP Moderate / Certified / L2 /
        SaaS / Public Cloud, so the group stays single-tier and
        the Moderate baseline is unchanged. Its source record
        carries no business categories (uncategorized in the
        source); the DeadRamp category is the census proposal,
        Education & Training."""
        sheet = _sheet(_load_specs(), "FR2135637226")
        self.assertEqual(sheet["vendor"], "Pearson VUE")
        self.assertEqual(sheet["product"], "Pearson Federal Cloud System")
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["business_categories_in_source"], [])
        self.assertEqual(sheet["deadramp_category"], "Education & Training")

    def test_description_equals_cached_source(self):
        """The addition sheet's description is the fork's own
        cached marketplace description under the group's
        original convention (stored stripped)."""
        sheet = _sheet(_load_specs(), "FR2135637226")
        self.assertEqual(
            sheet["description"],
            _raw_product("FR2135637226")["service_desc"].strip())

    def test_evidence_is_verbatim(self):
        """Every claim's evidence sentence appears verbatim in
        the fork's own description."""
        sheet = _sheet(_load_specs(), "FR2135637226")
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_census_citations_accounting(self):
        """Citation accounting, pinned with the twist: citation
        1 verifies as a strict verbatim substring and IS the
        enrollment/assessments evidence sentence. Citation 2
        does NOT verify strictly — the source text carries a
        line break inside the sentence ("assessments\\n to") —
        and verifies only whitespace-normalized. Neither is
        load-bearing: every claim rests on the description
        itself. Verification is not a claim, in either
        direction."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        cites = census["FR2135637226"]["citations"]
        self.assertEqual(len(cites), 2)
        sheet = _sheet(_load_specs(), "FR2135637226")
        desc = sheet["description"]
        self.assertIn(cites[0], desc)
        self.assertEqual(
            cites[0], EXPECTED_EVIDENCE["enrollment_registration"])
        self.assertNotIn(cites[1], desc)
        norm = lambda t: re.sub(r"\s+", " ", t)
        self.assertIn(norm(cites[1]), norm(desc))

    def test_no_exclusion_trap_for_newcomer(self):
        """No exclusion applied: the fork's source record
        carries no certified-services block, and its third
        sentence enumerates the fork's OWN subsystems inside
        its own FedRAMP boundary (Athena test drivers, OnVUE,
        IntelliVUE are Pearson VUE's own components of this
        offering) — an in-scope enumeration, not a catalogue of
        third-party hosted applications and not a scope-
        exclusion segment. Matched text is the full text."""
        self.assertEqual(
            _raw_product("FR2135637226")["certified_services"], [])
        desc = _sheet(_load_specs(), "FR2135637226")["description"]
        self.assertIn("FedRAMP boundary includes candidate registration",
                      desc)

    def test_proctoring_substance_no_family(self):
        """Proctoring accounting: the newcomer asserts online
        proctoring in its own words ("the OnVUE online
        proctoring platform"), retiring the union spec's named
        absence as a substance finding for the proctoring half —
        but no taxonomy family exists for proctoring, so no
        sheet claims one, and the gap gains a claimant in
        substance only. Identity proofing stays absent in both
        senses: no identity token anywhere in the description."""
        specs = _load_specs()
        desc = _sheet(specs, "FR2135637226")["description"]
        self.assertIn("online proctoring platform", desc)
        for s in specs:
            for c in s["functions_claimed"]:
                self.assertNotIn("proctor", c["function_id"])
        self.assertNotIn("identity", desc.lower())

    def test_near_miss_pins_pearson(self):
        """Pearson VUE: assessment-delivery substance is present
        in its own words; the neighbouring family tokens are
        absent, so the near-miss families stay at their shipped
        counts for this fork."""
        desc = _sheet(_load_specs(), "FR2135637226")["description"]
        low = desc.lower()
        # Substance present (claims and gaps, ADDENDUM sections
        # 2 and 5):
        self.assertIn("delivers assessments", low)
        self.assertIn("registered testing candidates", low)
        self.assertIn("candidate registration and scheduling", low)
        self.assertIn("reporting systems", low)
        self.assertIn("online proctoring", low)
        self.assertIn("infrastructure-as-a-service", low)
        self.assertIn("assessment programs", low)
        # Family tokens absent:
        self.assertNotIn("course", low)
        self.assertNotIn("training program", low)
        self.assertNotIn("platform-as-a-service", low)
        self.assertNotIn("multi-tenant", low)
        self.assertIsNone(re.search(r"certif|credential|licensure", low))
        self.assertNotIn("compliance", low)
        self.assertNotIn("content", low)
        self.assertNotIn("recording", low)
        self.assertNotIn("talent", low)
        self.assertNotIn("skills", low)
        self.assertIsNone(re.search(
            r"recruit|hiring|hire|onboard|workforce management",
            desc, re.IGNORECASE))
        self.assertIsNone(re.search(r"score|grad(e|ing|ed)", desc,
                                     re.IGNORECASE))
        self.assertNotIn("identity", low)
        self.assertNotIn("transcript", low)
        self.assertNotIn("notification", low)
        self.assertNotIn("reminder", low)
        self.assertNotIn("api", low)
        self.assertNotIn("stream", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """Substrate cases for the addition fork (ADDENDUM section
    3). The core is unchanged; each case runs the fork's
    described surface through the records form it presupposes."""

    def test_pearson_candidate_testing_flow(self):
        """Pearson VUE: an assessment program is registered
        (Core 1), a testing candidate is registered against it
        (Core 2, kind=registration), a candidate test session
        is scheduled (Core 7), and an assessment administration
        record is created against that session holding an item
        response verbatim with NO score or grade field (Core 4
        — scoring is Extended, 0/9 in this group), then read
        back through reporting over the records (Core 8). The
        Athena test-driver engine that would deliver the exam
        is Extended — nothing here delivers anything."""
        store, _course = make_store()
        program = store.create_course(
            "Agency Certification Exam Program", ADMIN,
            kind="program", code="EXAM-450")
        reg = store.create_enrollment(
            "carol", program["id"], INSTRUCTOR, kind="registration")
        self.assertEqual(reg["kind"], "registration")
        session = store.create_session(
            "Candidate test session", program["id"],
            "2026-06-10T09:00:00Z", INSTRUCTOR,
            ends_at="2026-06-10T11:00:00Z", kind="assessment",
            learner_ids=["carol"])
        self.assertEqual(session["kind"], "assessment")
        asm = store.create_assessment(
            "High-stakes certification exam", "carol", INSTRUCTOR,
            course_id=program["id"], session_id=session["id"])
        store.add_assessment_response(asm["id"], "item-1", "B", INSTRUCTOR)
        administered = store.set_assessment_state(
            asm["id"], "administered", INSTRUCTOR)
        self.assertEqual(administered["state"], "administered")
        record = store.get_assessment(asm["id"], ADMIN)
        self.assertNotIn("score", record)
        self.assertNotIn("grade", record)
        self.assertEqual(record["responses"],
                         [{"item_id": "item-1", "response": "B"}])
        report = store.report(ADMIN, as_of="2026-06-15")
        self.assertEqual(report["courses"], 2)
        self.assertEqual(report["enrollments"], 1)
        self.assertEqual(report["enrollments_by_course"],
                         {program["id"]: 1})
        self.assertEqual(report["sessions"], 1)
        self.assertEqual(report["assessments"], 1)
        self.assertEqual(report["assessments_by_state"]["administered"], 1)

    def test_pearson_candidate_compliance_derivation(self):
        """Pearson VUE: a compliance assignment over the exam
        program (the record form a testing program's upkeep
        presupposes) reads overdue past its due date with no
        completion record, and completed once a completed
        progress record exists — status derived at read, never
        stored (Core 6; the overdue assertion trips the group's
        signature _derive_status drill by exactly one)."""
        store = fresh_store()
        program = store.create_course(
            "Agency Certification Exam Program", ADMIN,
            kind="program", code="EXAM-450")
        assignment = store.create_compliance_assignment(
            "carol", program["id"], "2026-06-01", ADMIN)
        self.assertNotIn("status", assignment)
        summary = store.compliance_status(
            assignment["id"], ADMIN, as_of="2026-06-15")
        self.assertEqual(summary["status"], "overdue")
        self.assertFalse(summary["completed"])
        store.record_progress("carol", program["id"], "completed", INSTRUCTOR)
        summary = store.compliance_status(
            assignment["id"], ADMIN, as_of="2026-06-15")
        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["completed"])


if __name__ == "__main__":
    unittest.main()
