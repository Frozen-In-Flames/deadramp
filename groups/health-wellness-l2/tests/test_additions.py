"""Remainder additions (unit addition:health-wellness-l2): spec
integrity and one substrate case per addition fork.

Traces to: ADDENDUM.md for Group 18. The 3 previously uncategorized
forks (GTS VirtualHealth Platform, Solventum RevCycle, Somnoware)
were spec'd under the group's EXISTING 11-family taxonomy applied
verbatim -- the additions extractor parses the TAXONOMY literal out
of the shipped ``scratch/extract.py`` via ``ast`` (parsed, never
executed, never re-typed) before tagging. All 3 forks claim **zero**
families: the taxonomy's patterns are the original siblings' literal
phrases (glucose / CGM vocabulary, a Dexcom brand pipeline, Google
Cloud deployment prose), and the newcomers are a telehealth
platform, a revenue-cycle coding platform, and a sleep-medicine
platform. The zero-claim outcome is pinned here, not hidden, with
the near-miss substance asserted present in the descriptions.

The core is unchanged (no claimed family presupposes a records form
the build lacks), so each addition fork is additionally exercised
against the substrate through the records form its own described
surface presupposes: a telehealth visit is an activity record
(Core 6) with monitoring measurements (Core 4); revenue-cycle
reimbursement content presupposes coverage records (Core 7);
CPAP therapy progress is a plan record with derived status
(Core 5) over measurement records (Core 4). The GTS and Somnoware
cases derive plan/enrollment status and therefore trip on the
group's signature derivation mutant (see tests/README.md).
"""

import json
import os
import unittest

from health_helpers import ADMIN, CLINICIAN, fresh_store

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

ORIGINAL_ORDER = [
    "FR2000174962",  # Abbott, Inc. -- LibreView for US Government
    "FR2135180018",  # CuraPatient -- Composite Apps/ CuraPatient
    "FR2508262726",  # Dexcom Inc. -- Dexcom Clarity for Government
    "FR2309381948",  # Elekta Solutions -- Elekta ProKnow Federal
    "FR2210851632",  # GetWellNetwork -- Get Well Anywhere - Federal
]
UNIT_ORDER = [
    "FR2035860874",  # Global Telehealth Services, inc. -- GTS VirtualHealth Platform (GTS-VP)
    "FR2135915901",  # Solventum -- Solventum RevCycle Health Services Platform
    "FR2002367706",  # Somnoware Healthcare Systems -- Somnoware
]

# The literal claim table for the additions: every fork claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {
    "FR2035860874": [],
    "FR2135915901": [],
    "FR2002367706": [],
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM section 1/2: membership, order, literal claim table,
    verbatim descriptions, census citations, near-miss pins."""

    def test_sheet_count_and_order(self):
        """8 sheets: the shipped 5 untouched in place, then the 3
        additions in census unit order."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER)

    def test_membership_matches_remainder_unit(self):
        """The appended sheets are exactly the census unit's forks."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "addition:health-wellness-l2")
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs[5:]],
                         unit["fork_ids"])

    def test_literal_claim_table_all_zero(self):
        """Every addition fork claims zero families; pinned."""
        specs = _load_specs()
        for fork_id, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in _sheet(specs, fork_id)["functions_claimed"]]
            self.assertEqual(got, expected, fork_id)

    def test_group_totals_unchanged(self):
        """The additions add no claims: the group total stays 19 and
        3 of the group's 8 forks now carry zero claims."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 19)
        self.assertEqual(
            sum(1 for s in specs if not s["functions_claimed"]), 3)

    def test_addition_tier_fields(self):
        """All 3 additions are FedRAMP Moderate / L2 / SaaS, so the
        group stays single-tier and the baseline is unchanged."""
        specs = _load_specs()
        for fork_id in UNIT_ORDER:
            sheet = _sheet(specs, fork_id)
            self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
            self.assertEqual(sheet["cmmc_tier"], "L2")
            self.assertEqual(sheet["service_model"], ["SaaS"])
            self.assertEqual(sheet["deadramp_category"],
                             "Health & Wellness")

    def test_descriptions_equal_cached_source(self):
        """Each addition sheet's description is the fork's own cached
        marketplace description, verbatim."""
        with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
            dump = json.load(fh)
        prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        pmap = {p["id"]: p for p in prods}
        specs = _load_specs()
        for fork_id in UNIT_ORDER:
            self.assertEqual(
                _sheet(specs, fork_id)["description"],
                (pmap[fork_id].get("service_desc") or "").strip())

    def test_census_citations_verify_as_substrings(self):
        """All 4 census citations for the unit verify as verbatim
        substrings of the forks' own descriptions. Verification is
        not a claim: every cited sentence tags no family (see the
        claim table above)."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        census = {f["fork_id"]: f for f in rem["forks"]
                  if f["fork_id"] in UNIT_ORDER}
        self.assertEqual(sum(len(census[f]["citations"])
                             for f in UNIT_ORDER), 4)
        specs = _load_specs()
        for fork_id in UNIT_ORDER:
            desc = _sheet(specs, fork_id)["description"]
            for cite in census[fork_id]["citations"]:
                self.assertIn(cite, desc)

    def test_near_miss_pins_gts(self):
        """GTS: telehealth and clinical-data substance is present;
        the family phrases are absent."""
        desc = _sheet(_load_specs(), "FR2035860874")["description"]
        low = desc.lower()
        self.assertIn("real time telehealth visits", low)
        self.assertIn("video-teleconferencing", low)
        self.assertIn("clinical data", low)
        self.assertIn("integrates with rpm medical devices", low)
        self.assertNotIn("clinical metrics", low)
        self.assertNotIn("patient engagement", low)
        self.assertNotIn("integrated with emr", low)

    def test_near_miss_pins_solventum(self):
        """Solventum: coding/AI/reimbursement substance is present;
        the family phrases are absent ("automatic" is not
        "automated"; "AI-inclusive" is not the family's exact
        "Artificial Intelligence (AI) powered")."""
        desc = _sheet(_load_specs(), "FR2135915901")["description"]
        low = desc.lower()
        self.assertIn("automatic suggestion of cpt and icd codes", low)
        self.assertIn("ai-inclusive methodologies", low)
        self.assertIn("reimbursement content", low)
        self.assertIn("enterprise analytics reporting", low)
        self.assertNotIn("automated", low)
        self.assertNotIn("automates", low)
        self.assertNotIn("artificial intelligence (ai) powered", low)
        self.assertNotIn("justify reimbursement", low)

    def test_near_miss_pins_somnoware(self):
        """Somnoware: engagement-metrics / EMR-integration substance
        is present; the words "patient" and "engagement" never stand
        adjacent, and no family phrase appears."""
        desc = _sheet(_load_specs(), "FR2002367706")["description"]
        low = desc.lower()
        self.assertIn("engagement metrics", low)
        self.assertIn("integrations with all major diagnostic devices, "
                      "emr applications", low)
        self.assertIn("clinical intelligence", low)
        self.assertIn("care management console", low)
        self.assertNotIn("patient engagement", low)
        self.assertNotIn("clinical metrics", low)
        self.assertNotIn("integrated with emr", low)
        self.assertNotIn("care journey", low)
        self.assertNotIn("artificial intelligence (ai) powered", low)


class TestAdditionSubstrateCases(unittest.TestCase):
    """One substrate case per addition fork (ADDENDUM section 3).
    The core is unchanged; each case runs the fork's described
    surface through the records form it presupposes."""

    def test_gts_telehealth_visit_is_an_activity_record(self):
        """GTS-VP: a telehealth visit is a Core 6 activity record
        (the media channel is Extended -- no media/channel field
        exists in the shape), remote monitoring values are Core 4
        measurement records, and the follow-up plan derives overdue,
        carrying the enrollment with it (Core 3/5)."""
        store = fresh_store()
        program = store.create_program("Virtual Care", ADMIN)
        participant = store.create_participant("gts-patient-1", ADMIN)
        enrollment = store.create_enrollment(
            participant["id"], program["id"], CLINICIAN)
        visit = store.create_activity(
            participant["id"], "Telehealth visit", "2026-06-10T15:00:00",
            CLINICIAN, program_id=program["id"],
            ends_at="2026-06-10T15:30:00", kind="session")
        self.assertEqual(
            set(visit.keys()),
            {"id", "participant_id", "program_id", "title", "kind",
             "starts_at", "ends_at", "state", "created_by",
             "created_utc"})
        done = store.set_activity_state(visit["id"], "completed",
                                        CLINICIAN)
        self.assertEqual(done["state"], "completed")
        reading = store.record_measurement(
            participant["id"], "heart_rate", 72, "bpm", "2026-06-10",
            CLINICIAN, program_id=program["id"])
        self.assertEqual(reading["value"], 72)
        plan = store.create_plan(
            participant["id"], program["id"], "RPM follow-up",
            "2026-06-01", CLINICIAN)
        self.assertEqual(
            store.get_plan(plan["id"], ADMIN,
                           as_of="2026-06-15")["derived_status"],
            "overdue")
        self.assertEqual(
            store.get_enrollment(enrollment["id"], ADMIN,
                                 as_of="2026-06-15")["derived_status"],
            "overdue")

    def test_solventum_coverage_record_under_opaque_plan_ref(self):
        """Solventum: its reimbursement-content surface presupposes
        Core 7 coverage records -- an opaque plan_ref only, with
        derived upcoming / current / ended status and no insurer,
        member-number, or benefit field anywhere in the shape."""
        store = fresh_store()
        participant = store.create_participant("revcycle-case-1", ADMIN)
        elig = store.create_eligibility(
            participant["id"], "PLAN-REF-001", "2026-07-01", ADMIN,
            coverage_end="2026-12-31")
        # create returns the read view: the stored fields plus the
        # derived status -- and nothing else.
        self.assertEqual(
            set(elig.keys()),
            {"id", "participant_id", "program_id", "plan_ref",
             "coverage_start", "coverage_end", "created_by",
             "created_utc", "derived_status"})
        self.assertEqual(
            store.eligibility_status(elig["id"], ADMIN,
                                     as_of="2026-06-15"),
            {"id": elig["id"], "derived_status": "upcoming"})
        self.assertEqual(
            store.eligibility_status(elig["id"], ADMIN,
                                     as_of="2026-08-01")["derived_status"],
            "current")
        self.assertEqual(
            store.eligibility_status(elig["id"], ADMIN,
                                     as_of="2027-01-15")["derived_status"],
            "ended")

    def test_somnoware_cpap_plan_and_measurement_shapes(self):
        """Somnoware: CPAP therapy progress is a Core 5 plan record
        (current -> overdue -> completed, all derived at read, never
        stored) over Core 4 measurement records whose shape has no
        diagnosis field -- diagnosis content is Extended by
        construction in this group."""
        store = fresh_store()
        program = store.create_program(
            "Sleep Care Journey", ADMIN, kind="care_journey")
        participant = store.create_participant("somno-patient-1", ADMIN)
        msr = store.record_measurement(
            participant["id"], "ahi", 4.2, "events/hour", "2026-06-05",
            CLINICIAN, program_id=program["id"])
        self.assertEqual(
            set(msr.keys()),
            {"id", "participant_id", "program_id", "metric_name",
             "value", "unit", "recorded_on", "created_by",
             "created_utc"})
        plan = store.create_plan(
            participant["id"], program["id"], "CPAP therapy review",
            "2026-06-10", CLINICIAN, kind="care_plan")
        self.assertEqual(
            store.get_plan(plan["id"], ADMIN,
                           as_of="2026-06-01")["derived_status"],
            "current")
        self.assertEqual(
            store.get_plan(plan["id"], ADMIN,
                           as_of="2026-06-15")["derived_status"],
            "overdue")
        store.complete_plan(plan["id"], "2026-06-14", CLINICIAN)
        self.assertEqual(
            store.get_plan(plan["id"], ADMIN,
                           as_of="2026-06-15")["derived_status"],
            "completed")


if __name__ == "__main__":
    unittest.main()
