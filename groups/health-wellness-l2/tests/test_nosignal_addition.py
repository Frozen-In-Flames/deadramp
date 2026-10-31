"""No-signal addition (FR2220549818, CirrusMD): spec integrity and
one substrate case.

Traces to: ADDENDUM.md section 7 for Group 18. This fork sat in the
remainder census's ``no-signal-set``: its cached marketplace
description is generic SaaS / security / hosting boilerplate
(census: citations [], no_signal "prose_only"), so the census could
not cite a function for it. Its category was resolved afterwards by
the live-docs research pass (``remainder/nosignal_report.json``):
Health & Wellness, on the vendor's own sentence from its About page
(https://www.cirrusmd.com/about-cirrusmd). That sentence is pinned
here as the sheet's *classification* citation -- kept distinct from
claim evidence, and in fact asserted NOT to occur in the cached
description.

Spec'd under the group's EXISTING 11-family taxonomy applied
verbatim -- the no-signal extractor parses the TAXONOMY literal out
of the shipped ``scratch/extract.py`` via ``ast`` (parsed, never
executed, never re-typed) and, before tagging, reproduces all 8
shipped claim tables exactly (taxonomy-verbatim proof). CirrusMD
claims **zero** families: its description is delivery and posture
prose ("fully secure", "complies with HIPAA and GDPR",
multi-tenant community cloud), and the word "patient" occurs
nowhere in it. The zero-claim outcome is pinned here, not hidden,
with the near-miss substance asserted present in the description.

The core is unchanged (no claimed family presupposes a records form
the build lacks), so the fork is additionally exercised against the
substrate through the records form its described surface
presupposes: a virtual health chat visit is an activity record
(Core 6) -- the chat channel itself is an engine, and no field in
the shape can hold message content. The case derives plan /
enrollment status and therefore trips on the group's signature
derivation mutant (see tests/README.md).
"""

import json
import os
import subprocess
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
NOSIGNAL_ID = "FR2220549818"  # CirrusMD -- CirrusMD Virtual Health Chat for Government

# The literal claim table for the no-signal fork: it claims zero
# families under the taxonomy applied verbatim. Pinned, not hidden.
EXPECTED_CLAIMS = {NOSIGNAL_ID: []}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _sheet(specs, fork_id):
    return next(s for s in specs if s["fork_id"] == fork_id)


class TestNoSignalSpecIntegrity(unittest.TestCase):
    """ADDENDUM section 7: membership, shipped-sheet immutability,
    the literal zero-claim table, verbatim description, the
    classification citation pins, and the near-miss pins."""

    def test_sheet_count_and_order(self):
        """9 sheets: the shipped 5, the 3 remainder additions in
        unit order, then the no-signal sheet."""
        specs = _load_specs()
        self.assertEqual([s["fork_id"] for s in specs],
                         ORIGINAL_ORDER + UNIT_ORDER + [NOSIGNAL_ID])

    def test_shipped_sheets_deep_equal_git_head(self):
        """The 8 previously shipped sheets are deep-equal to git
        HEAD -- the append changed none of them."""
        head = subprocess.run(
            ["git", "-C", _REPO_ROOT, "show",
             "HEAD:groups/health-wellness-l2/specs/specs.json"],
            capture_output=True, text=True, check=True).stdout
        head_specs = json.loads(head)
        self.assertEqual(len(head_specs), 8)
        self.assertEqual(_load_specs()[:8], head_specs)

    def test_membership_is_the_nosignal_fork(self):
        """The appended sheet is exactly CirrusMD, the fork the
        census left in its no-signal set (citations [], flagged
        no_signal) and the live-docs pass resolved."""
        specs = _load_specs()
        sheet = _sheet(specs, NOSIGNAL_ID)
        self.assertEqual(sheet["vendor"], "CirrusMD")
        self.assertEqual(
            sheet["product"], "CirrusMD Virtual Health Chat for Government")
        self.assertEqual(
            sheet["source_url"],
            "https://www.fedramp.gov/marketplace/products/FR2220549818/")
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            rem = json.load(fh)
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == "no-signal-set")
        self.assertIn(NOSIGNAL_ID, unit["fork_ids"])
        census = next(f for f in rem["forks"]
                      if f["fork_id"] == NOSIGNAL_ID)
        self.assertTrue(census["no_signal"])
        self.assertEqual(census["citations"], [])

    def test_literal_claim_table_zero(self):
        """CirrusMD claims zero families; pinned."""
        specs = _load_specs()
        got = [c["function_id"]
               for c in _sheet(specs, NOSIGNAL_ID)["functions_claimed"]]
        self.assertEqual(got, EXPECTED_CLAIMS[NOSIGNAL_ID])

    def test_group_totals_unchanged(self):
        """The no-signal addition adds no claims: the group total
        stays 19 and 4 of the group's 9 forks now carry zero
        claims."""
        specs = _load_specs()
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in specs), 19)
        self.assertEqual(
            sum(1 for s in specs if not s["functions_claimed"]), 4)

    def test_tier_fields(self):
        """CirrusMD is FedRAMP Moderate / L2 / SaaS, FedRAMP
        Certified, Government Community Cloud -- the group stays
        single-tier and the baseline is unchanged."""
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["fedramp_impact_level"], "Moderate")
        self.assertEqual(sheet["cmmc_tier"], "L2")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(sheet["deployment_model"],
                         "Government Community Cloud")
        self.assertEqual(sheet["deadramp_category"], "Health & Wellness")

    def test_description_equals_cached_sources(self):
        """The sheet's description is the fork's own cached
        marketplace description, verbatim -- identical in the raw
        dataset and in remainder/uncovered.json."""
        with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
            dump = json.load(fh)
        prods = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
        pmap = {p["id"]: p for p in prods}
        raw_desc = (pmap[NOSIGNAL_ID].get("service_desc") or "").strip()
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "uncovered.json")) as fh:
            unc = json.load(fh)
        urec = next(r for r in unc if r["fork_id"] == NOSIGNAL_ID)
        sheet = _sheet(_load_specs(), NOSIGNAL_ID)
        self.assertEqual(sheet["description"], raw_desc)
        self.assertEqual(sheet["description"], urec["description"])

    def test_classification_fields_match_report(self):
        """The sheet's classification citation is exactly the
        live-docs report's entry: the verbatim sentence and its URL
        from remainder/nosignal_report.json, category Health &
        Wellness, status resolved. The sentence is the vendor's
        About-page prose, NOT marketplace text: it does not occur
        in the cached description, which is what keeps the
        classification citation distinct from claim evidence."""
        with open(os.path.join(_REPO_ROOT, "remainder",
                               "nosignal_report.json")) as fh:
            report = json.load(fh)
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
            "https://www.cirrusmd.com/about-cirrusmd")
        self.assertNotIn(sheet["classification_evidence"],
                         sheet["description"])

    def test_all_claim_evidence_verbatim(self):
        """Every claim's evidence, group-wide, is a verbatim
        substring of its own fork's description (vacuous for
        CirrusMD's empty table, run anyway)."""
        for sheet in _load_specs():
            for claim in sheet["functions_claimed"]:
                self.assertIn(claim["evidence"], sheet["description"])

    def test_near_miss_pins_cirrusmd(self):
        """CirrusMD: virtual-care / delivery / posture substance is
        present; every family phrase is absent, and the word
        "patient" occurs nowhere in the description."""
        desc = _sheet(_load_specs(), NOSIGNAL_ID)["description"]
        low = desc.lower()
        # Substance present.
        self.assertIn("virtual health chat", low)
        self.assertIn("agency care", low)
        self.assertIn("multi-tenant", low)
        self.assertIn("cloud-based service offering", low)
        self.assertIn("fully secure", low)
        self.assertIn("complies with hipaa and gdpr", low)
        # Family phrases absent.
        self.assertNotIn("patient", low)
        self.assertNotIn("care journey", low)
        self.assertNotIn("clinical metrics", low)
        self.assertNotIn("patient engagement", low)
        self.assertNotIn("google cloud", low)
        self.assertNotIn("google kubernetes engine", low)
        self.assertNotIn("multi-device accessibility", low)
        self.assertNotIn("web and mobile applications", low)
        self.assertNotIn("automated", low)
        self.assertNotIn("audit", low)


class TestNoSignalSubstrateCase(unittest.TestCase):
    """One substrate case for the no-signal fork (ADDENDUM section
    7). The core is unchanged; the case runs the fork's described
    surface through the records form it presupposes."""

    def test_cirrusmd_chat_visit_is_an_activity_record(self):
        """CirrusMD: a virtual health chat visit is a Core 6
        activity record (the chat channel is Extended -- no
        channel/message/transcript field exists in the shape, so
        no conversation content can be stored), and the care-team
        follow-up plan derives overdue, carrying the enrollment
        with it (Core 3/5)."""
        store = fresh_store()
        program = store.create_program("Virtual Care", ADMIN)
        participant = store.create_participant("cirrusmd-patient-1",
                                               ADMIN)
        enrollment = store.create_enrollment(
            participant["id"], program["id"], CLINICIAN)
        visit = store.create_activity(
            participant["id"], "Virtual health chat visit",
            "2026-06-10T15:00:00", CLINICIAN,
            program_id=program["id"], ends_at="2026-06-10T15:20:00",
            kind="session")
        self.assertEqual(
            set(visit.keys()),
            {"id", "participant_id", "program_id", "title", "kind",
             "starts_at", "ends_at", "state", "created_by",
             "created_utc"})
        done = store.set_activity_state(visit["id"], "completed",
                                        CLINICIAN)
        self.assertEqual(done["state"], "completed")
        plan = store.create_plan(
            participant["id"], program["id"], "Care team follow-up",
            "2026-06-01", CLINICIAN)
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
