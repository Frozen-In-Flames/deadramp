"""Singleton spec integrity and substrate cases for the Health &
Wellness L1 singleton (DeadRamp Phase 2 remainder, unit
new-singleton:Health & Wellness|L1).

Traces to: UNION-SPEC.md for the Health & Wellness L1 singleton.
The group's single fork (Itamar Medical / Itamar Dispatcher Cloud
(IDC)) was spec'd under the category's EXISTING 11-family taxonomy
applied verbatim -- the extractor (../scratch/extract.py) parses
the TAXONOMY literal out of Group 18's shipped
``scratch/extract.py`` via ``ast`` (parsed, never executed, never
re-typed) and reproduces Group 18's ORIGINAL shipped claim tables
exactly (19 claims, read from the original ship commit) before
tagging the newcomer.

The newcomer claims **zero families** -- pinned literally below,
not hidden. The taxonomy was defined from the original five forks'
glucose / CGM and patient-engagement vocabulary; this fork is a
home sleep-apnea test dispatcher (WatchPAT device initialization,
patient-management-system API integration, sleep-study data
transfer), and none of the taxonomy's literal phrases fires on any
of its three sentences. Raw hits equal claims (0 = 0); nothing was
removed before matching (the source record's certified_services is
empty, asserted here), and the near-misses are pinned per sentence:
substance tokens present, family phrases absent.

Citation accounting, pinned: the fork's single census citation
verifies as a strict verbatim substring -- it is the description's
FIRST sentence -- and tags no family. There are no claims, so no
claim rests on an uncited sentence either. Verification is not a
claim, in either direction.

The substrate cases exercise the shipped core as the newcomer
would use it: a home sleep-study session as a Core 6 activity
record (exact contract key set -- no diagnosis, result, or
device-data field exists), a study-administration value as a Core 4
measurement record, a coverage record under an opaque plan
reference deriving upcoming -> current -> ended (Core 7), and
member scope over those records. None of the cases touches the
plan derivation, so this file adds no failure to the group's
signature ``_derive_plan_status`` drill (tests/README.md).
"""

import ast
import json
import os
import re
import unittest

import health_helpers as H
from health.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))
_PARENT_DIR = os.path.join(_REPO_ROOT, "groups", "health-wellness-l2")

FORK_ID = "FR2212912561"
UNIT_ID = "new-singleton:Health & Wellness|L1"

ALL_FAMILIES = [
    "measurement_data",
    "analysis_reporting",
    "care_guidance",
    "patient_engagement",
    "claims_processing",
    "emr_integration",
    "ai_platform",
    "automation",
    "device_connectivity",
    "multi_device_access",
    "hosting_platform",
]

_S1 = ("The Zoll-Itamar Dispatcher Cloud (IDC) supports health care "
       "providers conducting home sleep apnea tests utilizing the "
       "WatchPAT device.")
_S2 = ("The provider integrates the IDC APIs into supported patient "
       "management systems to initialize WatchPAT devices and collect "
       "test results.")
_S3 = ("The patients take the sleep study using the device and a "
       "proprietary Mobile application that communicates and transfers "
       "sleep study data to IDC in a secure manner.")
DESCRIPTION = _S1 + " " + _S2 + " " + _S3


def _load_taxonomy():
    tree = ast.parse(open(os.path.join(
        _PARENT_DIR, "scratch", "extract.py")).read())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "TAXONOMY"
                for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError("TAXONOMY literal not found in parent extractor")


def _cache_product(fid):
    dump = json.load(open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")))
    fd = dump[3]["data"]["fedRAMPData"]
    return {p["id"]: p for p in fd["data"]["Products"]}[fid]


def _sentences(text):
    return re.split(r"(?<=[.!?])\s+", text.replace("\r", " "))


class TestSingletonSpec(unittest.TestCase):
    """Spec-sheet integrity for the singleton (UNION-SPEC.md)."""

    @classmethod
    def setUpClass(cls):
        cls.sheets = json.load(open(os.path.join(
            _GROUP_ROOT, "specs", "specs.json")))
        cls.sheet = cls.sheets[0]

    def test_single_sheet_and_census_membership(self):
        rem = json.load(open(os.path.join(_REPO_ROOT, "remainder.json")))
        unit = next(u for u in rem["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(len(self.sheets), 1)
        self.assertEqual([s["fork_id"] for s in self.sheets],
                         unit["fork_ids"])
        self.assertEqual(unit["fork_ids"], [FORK_ID])

    def test_taxonomy_verbatim_reproduces_original_shipped_tables(self):
        taxonomy = _load_taxonomy()
        self.assertEqual(len(taxonomy), 11)
        self.assertEqual([t[0] for t in taxonomy], ALL_FAMILIES)
        compiled = [(fid, re.compile(rx, re.I)) for fid, _, rx in taxonomy]
        parent_sheets = json.load(open(os.path.join(
            _PARENT_DIR, "specs", "specs.json")))[:5]
        total = 0
        for sheet in parent_sheets:
            p = _cache_product(sheet["fork_id"])
            desc = (p.get("service_desc") or "").strip()
            self.assertEqual(desc, sheet["description"])
            claims = []
            for tfid, rx in compiled:
                label = next(t[1] for t in taxonomy if t[0] == tfid)
                for s in _sentences(desc):
                    if rx.search(s):
                        ev = s.strip()
                        if len(ev) > 400:
                            ev = ev[:397] + "..."
                        claims.append({"function_id": tfid,
                                       "function": label, "evidence": ev})
                        break
            self.assertEqual(claims, sheet["functions_claimed"],
                             sheet["fork_id"])
            total += len(claims)
        self.assertEqual(total, 19)

    def test_zero_claim_table_is_literal(self):
        self.assertEqual(self.sheet["functions_claimed"], [])
        counts = json.load(open(os.path.join(
            _GROUP_ROOT, "scratch", "function_counts.json")))
        self.assertEqual(counts, {fid: 0 for fid in ALL_FAMILIES})
        # Recompute: no taxonomy pattern fires on any sentence.
        compiled = [(fid, re.compile(rx, re.I))
                    for fid, _, rx in _load_taxonomy()]
        for s in _sentences(self.sheet["description"]):
            for tfid, rx in compiled:
                self.assertIsNone(rx.search(s), (tfid, s))

    def test_tier_fields_recorded_as_is(self):
        # LI-SaaS recorded as-is, never rounded to Low.
        self.assertEqual(self.sheet["fedramp_impact_level"], "LI-SaaS")
        self.assertEqual(self.sheet["cmmc_tier"], "L1")
        self.assertEqual(self.sheet["authorization_status"],
                         "FedRAMP Certified")
        self.assertEqual(self.sheet["deployment_model"], "Public Cloud")
        self.assertEqual(self.sheet["service_model"], ["SaaS"])
        self.assertEqual(self.sheet["business_categories_in_source"], [])
        forks = json.load(open(os.path.join(_REPO_ROOT, "forks.json")))
        rec = next(f for f in forks
                   if f["source_url"].rstrip("/").endswith(FORK_ID))
        self.assertEqual(rec["category"], "Uncategorized (none in source)")
        self.assertEqual(rec["fedramp_impact_level"], "LI-SaaS")

    def test_description_verbatim_against_cache(self):
        p = _cache_product(FORK_ID)
        self.assertEqual(self.sheet["description"],
                         (p.get("service_desc") or "").strip())
        self.assertEqual(self.sheet["description"], DESCRIPTION)
        self.assertEqual(self.sheet["vendor"], "Itamar Medical")
        self.assertEqual(self.sheet["product"],
                         "Itamar Dispatcher Cloud (IDC)")

    def test_census_citation_verifies_and_tags_nothing(self):
        rem = json.load(open(os.path.join(_REPO_ROOT, "remainder.json")))
        entry = next(f for f in rem["forks"] if f["fork_id"] == FORK_ID)
        self.assertEqual(entry["proposed_category"], "Health & Wellness")
        self.assertEqual(len(entry["citations"]), 1)
        citation = entry["citations"][0]
        self.assertEqual(citation, _S1)
        self.assertIn(citation, self.sheet["description"])
        check = json.load(open(os.path.join(
            _GROUP_ROOT, "scratch", "citation_check.json")))
        self.assertTrue(check[citation]["verbatim_substring"])
        self.assertTrue(check[citation]["is_sentence"])
        self.assertFalse(check[citation]["tags_family"])

    def test_no_exclusion_accounting(self):
        # No third-party catalogue existed to exclude, and nothing
        # was removed before matching: raw hits == claims == 0.
        p = _cache_product(FORK_ID)
        self.assertEqual(p.get("certified_services") or [], [])
        smap = json.load(open(os.path.join(
            _GROUP_ROOT, "scratch", "sentence_map.json")))
        self.assertEqual(smap["sentences"], [_S1, _S2, _S3])
        self.assertEqual(smap["per_sentence_hits"],
                         {"0": [], "1": [], "2": []})
        self.assertEqual(smap["claim_sentence_indices"], {})

    def test_near_miss_pins(self):
        desc = self.sheet["description"]
        low = desc.lower()
        # Substance present, in the fork's own words:
        for token in ("integrates the idc apis", "patient management systems",
                      "initialize watchpat devices", "collect test results",
                      "mobile application", "transfers sleep study data",
                      "in a secure manner", "home sleep apnea tests"):
            self.assertIn(token, low)
        # Family phrases absent (the patterns were NOT loosened):
        for phrase in ("integration with client systems", "integrated with emr",
                       "connect their dexcom clarity data",
                       "upload cgm user receiver data",
                       "web and mobile applications",
                       "multi-device accessibility",
                       "artificial intelligence (ai) powered",
                       "glucose", "clinical metrics", "automated", "automates",
                       "google cloud", "survey patients", "patient engagement"):
            self.assertNotIn(phrase, low)
        # Named-absence token checks at this tier: telehealth media,
        # descriptive audit, descriptive access control.
        for token in ("video", "virtual", "telehealth", "visit",
                      "audit", "access"):
            self.assertNotIn(token, low)


class TestSingletonSubstrate(unittest.TestCase):
    """The carried substrate in the newcomer's shape."""

    def setUp(self):
        self.store = H.fresh_store()
        self.program = self.store.create_program(
            "Home Sleep Testing", H.ADMIN, code="HST-101")
        self.participant = self.store.create_participant("carol", H.ADMIN)
        self.store.create_enrollment(
            self.participant["id"], self.program["id"], H.CLINICIAN)

    def test_sleep_study_session_is_an_activity_record(self):
        act = self.store.create_activity(
            self.participant["id"], "Home sleep study",
            "2026-06-01T22:00:00+00:00", H.CLINICIAN,
            program_id=self.program["id"],
            ends_at="2026-06-02T06:00:00+00:00", kind="session")
        # Exact contract key set: no diagnosis, result, or
        # device-data field exists in the shape.
        self.assertEqual(set(act.keys()), {
            "id", "participant_id", "program_id", "title", "kind",
            "starts_at", "ends_at", "state", "created_by", "created_utc"})
        self.assertEqual(act["kind"], "session")
        self.assertEqual(act["state"], "scheduled")
        done = self.store.set_activity_state(act["id"], "completed",
                                             H.CLINICIAN)
        self.assertEqual(done["state"], "completed")

    def test_study_administration_measurement_shape(self):
        msr = self.store.record_measurement(
            self.participant["id"], "sleep_study_duration", 7.5, "hours",
            "2026-06-02", H.CLINICIAN, program_id=self.program["id"])
        self.assertEqual(set(msr.keys()), {
            "id", "participant_id", "program_id", "metric_name", "value",
            "unit", "recorded_on", "created_by", "created_utc"})
        self.assertNotIn("diagnosis", msr)
        self.assertNotIn("note", msr)

    def test_coverage_record_derives_upcoming_current_ended(self):
        elg = self.store.create_eligibility(
            self.participant["id"], "PLAN-HST-001", "2026-01-01",
            H.ADMIN, program_id=self.program["id"],
            coverage_end="2026-12-31")
        self.assertEqual(set(elg.keys()), {
            "id", "participant_id", "program_id", "plan_ref",
            "coverage_start", "coverage_end", "created_by", "created_utc",
            "derived_status"})
        self.assertNotIn("insurer", elg)
        self.assertNotIn("member_number", elg)
        sid = self.store.eligibility_status
        self.assertEqual(sid(elg["id"], H.ADMIN, as_of="2025-12-15")
                         ["derived_status"], "upcoming")
        self.assertEqual(sid(elg["id"], H.ADMIN, as_of="2026-06-01")
                         ["derived_status"], "current")
        self.assertEqual(sid(elg["id"], H.ADMIN, as_of="2027-02-01")
                         ["derived_status"], "ended")

    def test_member_scope_own_records_only(self):
        act = self.store.create_activity(
            self.participant["id"], "Home sleep study",
            "2026-06-01T22:00:00+00:00", H.CLINICIAN,
            program_id=self.program["id"], kind="session")
        other = self.store.create_participant("dave", H.ADMIN)
        other_act = self.store.create_activity(
            other["id"], "Home sleep study", "2026-06-03T22:00:00+00:00",
            H.CLINICIAN, program_id=self.program["id"], kind="session")
        # carol the member reads her own record; dave's is denied
        # on get and excluded from lists.
        self.assertEqual(
            self.store.get_activity(act["id"], H.MEMBER)["id"], act["id"])
        with self.assertRaises(PermissionDenied):
            self.store.get_activity(other_act["id"], H.MEMBER)
        mine = self.store.list_activities(H.MEMBER)
        self.assertEqual([a["id"] for a in mine], [act["id"]])


if __name__ == "__main__":
    unittest.main()
