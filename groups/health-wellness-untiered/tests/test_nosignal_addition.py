"""No-signal addition (FR2700137029, HealthEdge): spec integrity
and one substrate case.

Traces to: ADDENDUM.md (this group). This fork sat in the remainder
census's ``no-signal-set``: its cached marketplace description is a
single vague sentence about an agentic operational/financial
platform for payers and agencies (census: citations [],
no_signal "prose_only", "no specific function named"), so the
census could cite no function for it. Its category was resolved
afterwards by the live-docs research pass
(``remainder/nosignal_report.json``): Health & Wellness, on a
HealthEdge press-release sentence hosted on healthedge.com (the
vendor's own site), recorded in remainder/NOSIGNAL.md at
**suite level** — the sentence describes the integrated suite as
a whole, not a component of it. That sentence is pinned here as
the sheet's *classification* citation — kept distinct from claim
evidence, and in fact asserted NOT to occur in the cached
description.

Spec'd under the set's EXISTING 11-family taxonomy applied
verbatim — the no-signal extractor AST-parses the taxonomy out of
the founding group's extractor (parsed, never executed, never
re-typed) and, before tagging, reproduces both the founding
group's original shipped claim tables (5 sheets, 19 claims,
deep-equal) and this set's 3 shipped claim tables exactly
(taxonomy-verbatim proofs). HealthEdge claims **zero** families:
its one-sentence description ("payers", "agentic platform of
operational infrastructure", "financial edge") contains no family
phrase. The zero-claim outcome is pinned here, not hidden, with
the near-miss substance asserted present in the description.

Tier discipline: the sheet records the source's impact level
as-is ("Unknown") with ``cmmc_tier`` null, exactly like the set's
shipped sheets — the addition changes no tier, asserts no
baseline, and documents no new control claim (the description
carries no control language at all; see the pins below).

The core is unchanged (no claimed family presupposes a records
form the build lacks), so the fork is additionally exercised
against the substrate through the records forms its described
surface presupposes: a payer-side coverage record is an
eligibility record (Core 7) under an opaque ``plan_ref`` only —
no insurer name, member number, or benefit field exists in the
shape — and an operations plan / enrollment over it derive status
(Core 3/5). The case derives plan status and therefore trips on
the set's signature derivation mutant (see tests/README.md).
"""

import json
import os
import subprocess
import unittest

from health_helpers import ADMIN, CLINICIAN, fresh_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_DIR = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_DIR))

SET_ORDER = [
    "FR2634047811",  # 86Borders LLC -- 86Borders ConnectAllCare
    "FR2633734921",  # Elvo -- Elvo
    "FR1825232355",  # WellHive Holdings, LLC -- WellHive
]
NOSIGNAL_ID = "FR2700137029"  # HealthEdge Software, Inc. -- HealthEdge Integrated Solution Suite

# The literal claim table for the no-signal fork: it claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {NOSIGNAL_ID: []}


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _load_specs():
    return _load(os.path.join(_GROUP_DIR, "specs", "specs.json"))


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


class TestNoSignalSpecIntegrity(unittest.TestCase):
    """ADDENDUM: membership, shipped-sheet immutability, the
    literal zero-claim table, tier discipline, verbatim
    description, the classification citation pins, and the
    near-miss pins."""

    def test_sheet_count_and_order(self):
        """4 sheets: the set's 3 shipped sheets in shipped order,
        then the no-signal sheet appended."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         SET_ORDER + [NOSIGNAL_ID])

    def test_shipped_sheets_deep_equal_git_head(self):
        """The 3 previously shipped sheets are deep-equal to git
        HEAD -- the append changed none of them.

        Era rescope (final GAPS batch, 2026-11-07): at this
        module's own ship, git HEAD still held the 3 pre-append
        sheets; HEAD now holds all 4 (this unit's sheet included,
        appended by that same ship). The pin is therefore scoped
        to this unit's own era slice -- the first 3 HEAD sheets,
        which are exactly the sheets that existed before the
        append -- preserving the pin's exact strength: none of
        the pre-existing sheets may change."""
        head = subprocess.run(
            ["git", "-C", _ROOT, "show",
             "HEAD:groups/health-wellness-untiered/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        head_specs = json.loads(head)
        self.assertEqual(_load_specs()[:3], head_specs[:3])

    def test_membership_is_the_nosignal_fork(self):
        """The appended sheet is exactly HealthEdge, the fork the
        census left in its no-signal set (citations [], flagged
        no_signal) and the live-docs pass resolved."""
        specs = _load_specs()
        sheet = _sheet(specs, NOSIGNAL_ID)
        self.assertEqual(sheet["vendor"], "HealthEdge Software, Inc.")
        self.assertEqual(sheet["product"],
                         "HealthEdge Integrated Solution Suite")
        self.assertEqual(
            sheet["source_url"],
            "https://www.fedramp.gov/marketplace/products/FR2700137029/")
        rem = _load(os.path.join(_ROOT, "remainder.json"))
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn(NOSIGNAL_ID, unit["fork_ids"])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == NOSIGNAL_ID)
        self.assertTrue(census["no_signal"])
        self.assertEqual(census["citations"], [])

    def test_literal_claim_table_zero(self):
        """HealthEdge claims zero families; pinned."""
        specs = _load_specs()
        got = [c["function_id"]
               for c in _sheet(specs, NOSIGNAL_ID)["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[NOSIGNAL_ID])

    def test_set_totals_unchanged(self):
        """The no-signal addition adds no claims: the set total
        stays 1 (86Borders patient_engagement) and 3 of the 4
        sheets now carry zero claims."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 1)
        self.assertEqual(
            sum(1 for s in specs if not s["functions_claimed"]), 3)

    def test_tier_discipline_on_new_sheet(self):
        """Tier null, exactly as the set's shipped sheets: impact
        recorded as the source has it ("Unknown"), cmmc_tier
        null, no baseline asserted by the sheet."""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["fedramp_impact_level"], "Unknown")
        self.assertIsNone(sheet["cmmc_tier"])
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["authorization_status"],
                         "Initial Implementation")
        self.assertEqual(sheet["deployment_model"],
                         "Government-Only Cloud")
        self.assertEqual(sheet["deadramp_category"], "Health & Wellness")

    def test_description_equals_cached_sources(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim -- identical in the raw
        dataset and in remainder/uncovered.json."""
        dump = _load(os.path.join(_ROOT, "raw", "data_dump.json"))
        prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        pmap = {p["id"]: p for p in prods}
        raw_desc = (pmap[NOSIGNAL_ID].get("service_desc") or "").strip()
        unc = {r["fork_id"]: r
               for r in _load(os.path.join(_ROOT, "remainder",
                                           "uncovered.json"))}
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["description"], raw_desc)
        self.assertEqual(sheet["description"],
                         unc[NOSIGNAL_ID]["description"])

    def test_classification_fields_match_report(self):
        """The sheet's classification citation is exactly the
        live-docs report's entry: the verbatim sentence and its
        URL from remainder/nosignal_report.json, category Health
        & Wellness, status resolved, not a new category. The
        sentence is the vendor's press-release prose (suite
        level), NOT marketplace text: it does not occur in the
        cached description, which is what keeps the classification
        citation distinct from claim evidence."""
        report = _load(os.path.join(_ROOT, "remainder",
                                    "nosignal_report.json"))
        rep = next(r for r in report if r["fork_id"] == NOSIGNAL_ID)
        self.assertEqual(rep["status"], "resolved")
        self.assertEqual(rep["category_proposal"], "Health & Wellness")
        self.assertFalse(rep["is_new_category"])
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["classification_evidence"],
                         rep["evidence_sentence"])
        self.assertEqual(sheet["classification_source_url"],
                         rep["source_url"])
        self.assertEqual(
            sheet["classification_source_url"],
            "https://healthedge.com/press-release/healthedge-and-"
            "healthproof-merge-creating-disruptive-ai-powered-"
            "healthcare-payer-technology-and-services-leader/")
        self.assertNotIn(sheet["classification_evidence"],
                         sheet["description"])

    def test_all_claim_evidence_verbatim(self):
        """Every claim's evidence, set-wide, is a verbatim
        substring of its own fork's description under the founding
        normalization (carriage returns become spaces; vacuous for
        HealthEdge's empty table, run anyway)."""
        for sheet in _load_specs():
            norm = sheet["description"].replace("\r", " ")
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], norm,
                              f"{sheet['fork_id']} {claim['function_id']}")

    def test_near_miss_pins_healthedge(self):
        """HealthEdge: payer-operations / agentic-platform
        substance is present; every family phrase is absent, the
        word "patient" occurs nowhere, and no control language of
        any family occurs (the documented-control-claims effect is
        therefore nil)."""
        desc = _sheet(_load_specs(), NOSIGNAL_ID)["description"]
        low = desc.lower()
        # Substance present. (The cached description is
        # hard-wrapped: "financial\nedge" is split across lines,
        # so that phrase is checked on the whitespace-normalized
        # text; every other check runs on the raw text.)
        self.assertIn("payers", low)
        self.assertIn("agentic", low)
        self.assertIn("integrated solution suite", low)
        self.assertIn("operational", low)
        self.assertIn("financial edge", " ".join(low.split()))
        # Family phrases absent.
        self.assertNotIn("patient", low)
        self.assertNotIn("artificial intelligence (ai) powered", low)
        self.assertNotIn("automated", low)
        self.assertNotIn("automates", low)
        self.assertNotIn("medical claims processing", low)
        self.assertNotIn("justify reimbursement", low)
        self.assertNotIn("integrated with emr", low)
        self.assertNotIn("integration with client systems", low)
        self.assertNotIn("clinical metrics", low)
        self.assertNotIn("scorecards", low)
        self.assertNotIn("care journey", low)
        self.assertNotIn("patient engagement", low)
        self.assertNotIn("google cloud", low)
        self.assertNotIn("google kubernetes engine", low)
        self.assertNotIn("multi-device accessibility", low)
        # Control language absent (no documented control claim).
        self.assertNotIn("security", low)
        self.assertNotIn("hipaa", low)
        self.assertNotIn("audit", low)
        self.assertNotIn("access control", low)
        self.assertNotIn("encrypt", low)


class TestNoSignalSubstrateCase(unittest.TestCase):
    """One substrate case for the no-signal fork (ADDENDUM). The
    core is unchanged; the case runs the fork's described surface
    through the records forms it presupposes."""

    def test_healthedge_coverage_record_and_derived_statuses(self):
        """HealthEdge: a payer-side coverage record is a Core 7
        eligibility record under an opaque ``plan_ref`` only (the
        exact key set holds no insurer name, member number, or
        benefit field), its status derives upcoming -> current ->
        ended across the coverage window, and an operations plan
        over the enrollment derives overdue, carrying the
        enrollment with it (Core 3/5)."""
        store = fresh_store()
        program = store.create_program("Health Plan Operations", ADMIN)
        participant = store.create_participant("healthedge-member-1",
                                               ADMIN)
        enrollment = store.create_enrollment(
            participant["id"], program["id"], CLINICIAN)
        coverage = store.create_eligibility(
            participant["id"], "healthedge-plan-ref", "2026-06-01",
            ADMIN, program_id=program["id"], coverage_end="2026-06-30")
        self.assertEqual(
            set(coverage.keys()),
            {"id", "participant_id", "program_id", "plan_ref",
             "coverage_start", "coverage_end", "created_by",
             "created_utc", "derived_status"})
        for forbidden in ("insurer", "insurer_name", "member_number",
                          "benefits", "diagnosis", "note"):
            self.assertNotIn(forbidden, coverage)
        self.assertEqual(
            store.eligibility_status(coverage["id"], ADMIN,
                                     as_of="2026-05-15"),
            {"id": coverage["id"], "derived_status": "upcoming"})
        self.assertEqual(
            store.get_eligibility(coverage["id"], ADMIN,
                                  as_of="2026-06-15")["derived_status"],
            "current")
        self.assertEqual(
            store.eligibility_status(coverage["id"], ADMIN,
                                     as_of="2026-07-01")["derived_status"],
            "ended")
        plan = store.create_plan(
            participant["id"], program["id"],
            "Payer operations follow-up", "2026-06-01", CLINICIAN)
        self.assertEqual(
            store.get_plan(plan["id"], ADMIN,
                           as_of="2026-06-15")["derived_status"],
            "overdue")
        self.assertEqual(
            store.get_enrollment(enrollment["id"], ADMIN,
                                 as_of="2026-06-15")["derived_status"],
            "overdue")


if __name__ == "__main__":
    unittest.main()
