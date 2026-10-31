"""Remainder addition — Law Enforcement L3-adjacent (unit
``addition:law-enforcement-l3``).

Traces to: ADDENDUM.md §§1–3 — the 1 previously uncategorized fork
(TRAPWIRE Threat Detection and Analysis System) spec'd under the
group's existing 9-family taxonomy applied verbatim, joining two
zero-claim originals (Cellebrite Government Cloud, Magnet One),
and the substrate cases the newcomer's shape exercises against
the unchanged carried Core.

Spec-integrity pins: sheet count / append order / membership
against ``remainder.json``; the literal claim tables (all three
sheets empty — the newcomer is the group's third zero-claim
sheet, with 0 raw hits across all 9 families); descriptions equal
to the cached marketplace text; both census citations verifying
verbatim and tagging nothing (verification is not a claim, in
either direction); the near-miss pins recorded in ADDENDUM §2
("Cross-organizational collaboration" is not the verbatim
``collaboration`` phrase; "secure web access" is not "secure
access controls"; the description never says "cloud" at all); and
the category-discipline pins: no facial-recognition, surveillance,
camera/sensor, or predictive-policing token exists in the text,
while "real-time" threat detection and alerting IS described in
the fork's own words and is booked as its described function
(ADDENDUM §5), not attributed from reputation and not hidden.
"""

import json
import os
import re
import unittest

import lawenf_helpers as H
from lawenf.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

UNIT_ID = "addition:law-enforcement-l3"
UNIT_ORDER = ["F1602057825A"]
ORIGINALS = ["FR2421035110", "FR2616545789"]

ALL_FAMILIES = ["legal_research", "legal_search",
                "citation_validation", "document_management",
                "collaboration", "editorial_enhancement",
                "practice_guidance", "access_control",
                "hosting_platform"]

EXPECTED_CLAIMS = {
    "FR2421035110": [],
    "FR2616545789": [],
    "F1602057825A": [],
}

CITATION_1 = ("TRAPWIRE is a software platform for detecting and "
              "alerting on threats against your assets and personnel "
              "in real-time.")
CITATION_2 = ("The TRAPWIRE Threat Detection and Analysis System "
              "brings security organizations into a protection "
              "network that detects and alerts on mutual threats "
              "spanning time and geography, allowing users to break "
              "down stovepipes and interdict threats before they "
              "materialize into successful criminal or terrorist "
              "acts.")


def load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def load_raw_descriptions(ids):
    raw = json.load(open(os.path.join(_ROOT, "raw", "data_dump.json")))
    found = {}

    def walk(o):
        if isinstance(o, dict):
            if o.get("id") in ids and "service_desc" in o:
                found[o["id"]] = o["service_desc"]
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(raw)
    return found


class TestAdditionSpecIntegrity(unittest.TestCase):
    """ADDENDUM §1/§2 — membership, claim tables, verbatim text."""

    def setUp(self):
        self.specs = load_specs()
        self.by_id = {s["fork_id"]: s for s in self.specs}

    def test_sheet_count_order_and_membership(self):
        """3 sheets: the 2 originals, then the unit's 1 fork."""
        self.assertEqual([s["fork_id"] for s in self.specs],
                         ORIGINALS + UNIT_ORDER)
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        unit = next(u for u in remainder["build_units"]
                    if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], UNIT_ORDER)
        self.assertEqual(unit["extends_group"], "law-enforcement-l3")
        sheet = self.by_id["F1602057825A"]
        self.assertEqual(sheet["vendor"], "TRAPWIRE")
        self.assertEqual(sheet["product"],
                         "TRAPWIRE Threat Detection and Analysis System")
        self.assertEqual(sheet["deadramp_category"], "Law Enforcement")
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")
        self.assertEqual(sheet["authorization_status"], "FedRAMP Certified")
        self.assertEqual(sheet["service_model"], ["SaaS"])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        # Uncategorized in the source; the census assignment to
        # Law Enforcement is what this sheet records (ADDENDUM §1).
        self.assertEqual(sheet["business_categories_in_source"], [])

    def test_claim_tables_pinned_all_zero(self):
        """The literal claim tables: founder pair and newcomer all
        empty; the group total stays 0 claims across 3 forks, and
        every one of the 9 families stands at 0 of 3."""
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)
        total = sum(len(s["functions_claimed"]) for s in self.specs)
        self.assertEqual(total, 0)
        claiming = [s["fork_id"] for s in self.specs
                    if s["functions_claimed"]]
        self.assertEqual(claiming, [])  # 0 of 3 claiming
        counts = {}
        for s in self.specs:
            for c in s["functions_claimed"]:
                counts[c["function_id"]] = counts.get(c["function_id"], 0) + 1
        self.assertEqual(counts, {})
        for fam in ALL_FAMILIES:
            self.assertNotIn(fam, counts)

    def test_descriptions_match_cache(self):
        """All three descriptions equal the cached marketplace text,
        and the newcomer's record carries no certified-services
        catalogue (no exclusion question arises — ADDENDUM §1)."""
        raw = load_raw_descriptions(set(ORIGINALS + UNIT_ORDER))
        self.assertEqual(set(raw), set(ORIGINALS + UNIT_ORDER))
        for fid in ORIGINALS + UNIT_ORDER:
            self.assertEqual(self.by_id[fid]["description"], raw[fid], fid)

    def test_census_citations_verify_and_tag_nothing(self):
        """Both census citations verify verbatim (2/2) — and neither
        is a claim: the sheet they classify carries an empty claim
        table. Verification is not a claim, in either direction
        (ADDENDUM §2)."""
        remainder = json.load(open(os.path.join(_ROOT, "remainder.json")))
        fork = next(f for f in remainder["forks"]
                    if f["fork_id"] == "F1602057825A")
        self.assertEqual(fork["build_unit"], UNIT_ID)
        self.assertEqual(fork["current_category"],
                         "Uncategorized (none in source)")
        self.assertEqual(len(fork["citations"]), 2)
        desc = self.by_id["F1602057825A"]["description"]
        self.assertEqual(fork["citations"], [CITATION_1, CITATION_2])
        for cite in fork["citations"]:
            self.assertIn(cite, desc)
        self.assertEqual(
            self.by_id["F1602057825A"]["functions_claimed"], [])

    def test_near_miss_pins(self):
        """ADDENDUM §2 near-misses, pinned at the token level."""
        desc = self.by_id["F1602057825A"]["description"]
        # collaboration: the substance is everywhere, the verbatim
        # taxonomy phrase nowhere.
        self.assertIn("Cross-organizational collaboration", desc)
        self.assertIn("may collaborate with", desc)
        self.assertIn("information sharing", desc)
        self.assertNotIn("save, annotate, share and collaborate", desc)
        # access_control: "secure web access" (twice) is access
        # prose, not the verbatim phrase "secure access controls".
        self.assertEqual(desc.count("secure web access"), 2)
        self.assertNotIn("secure access controls", desc)
        # hosting_platform: a SaaS offering, yet the description
        # never says "cloud" at all (the Public Cloud deployment
        # model is the source record's field, not description text).
        self.assertIn("software-as-a-service offering", desc)
        self.assertNotIn("secure cloud environment", desc)
        self.assertNotIn("cloud", desc.lower())
        # legal_search / document_management: no token of either.
        self.assertNotIn("search", desc.lower())
        self.assertNotIn("document", desc.lower())

    def test_category_discipline_pins(self):
        """Capabilities are attributed only when the fork's own text
        states them (ADDENDUM §2/§5): facial recognition,
        surveillance, camera/sensor monitoring, and predictive
        policing appear NOWHERE in the text and are not attributed;
        real-time detection/alerting and interdiction ARE the
        fork's own words, booked as its described functions.
        "criminal" occurs exactly once, naming acts interdicted —
        not criminal records or history data of any kind."""
        desc = self.by_id["F1602057825A"]["description"]
        low = desc.lower()
        for token in ("facial", "recognition", "surveillance",
                      "camera", "sensor", "predict"):
            self.assertNotIn(token, low, token)
        self.assertIn("real-time", low)
        self.assertIn("interdict threats before they materialize", desc)
        self.assertEqual(low.count("criminal"), 1)
        self.assertIn("criminal or terrorist acts", desc)
        self.assertNotIn("criminal history", low)
        self.assertNotIn("criminal records", low)


class TestTrapwireSubstrate(unittest.TestCase):
    """ADDENDUM §3 — the carried substrate exercised in the
    newcomer's shape: a protection network is a membership
    boundary (Core 1 — the records-side analogue of the fork's
    originator control: each network owns its records and
    non-members see nothing), and a report exists in the substrate
    only as registry metadata + checksum with verify-by-content
    (Cores 3–4), a digest-only saved search (Core 5), and counts
    on read (Core 8). The newcomer claims no Core family; these
    cases claim none on its behalf. The detection, analysis,
    alerting, sharing, and notification engines themselves are
    Extended (ADDENDUM §5) — nothing here detects or alerts."""

    def test_protection_network_membership_boundary(self):
        """An outsider to the network matter can neither read the
        matter nor list its records: membership is the boundary,
        enforced before any record exists. (This is the additions
        case the membership-guard drill trips — tests/README.md.)
        """
        store, _audit, matter = H.make_store()
        with self.assertRaises(PermissionDenied):
            store.get_matter(matter["id"], H.OUTSIDER)
        with self.assertRaises(PermissionDenied):
            store.list_documents(matter["id"], H.OUTSIDER)
        # Members inside the boundary read normally.
        self.assertEqual(store.get_matter(matter["id"], H.VIEWER)["id"],
                         matter["id"])

    def test_report_record_integrity_and_counts(self):
        """A filed report's record: metadata + SHA-256 only,
        verify-by-content matching the exact bytes and rejecting
        altered bytes; a saved search stored as a digest; the
        matter report counting records on read."""
        store, _audit, matter = H.make_store()
        doc = store.register_document(matter["id"], "REPORT-REF-001",
                                      H.DOC_SHA256, len(H.DOC_CONTENT),
                                      H.MEMBER)
        self.assertEqual(doc["status"], "registered")
        exact = store.verify_document(matter["id"], doc["id"],
                                      H.DOC_CONTENT, H.MEMBER)
        self.assertTrue(exact["matches"])
        altered = store.verify_document(matter["id"], doc["id"],
                                        H.DOC_CONTENT + b" ", H.MEMBER)
        self.assertFalse(altered["matches"])
        saved = store.save_search(matter["id"], "SEARCH-REF-001",
                                  H.QUERY_SHA256, 7, H.MEMBER)
        self.assertEqual(saved["query_sha256"], H.QUERY_SHA256)
        self.assertNotIn(H.QUERY_TEXT,
                         json.dumps(saved))
        report = store.matter_report(matter["id"], H.MEMBER)
        self.assertEqual(report["member_count"], 2)
        self.assertEqual(report["documents_by_status"],
                         {"registered": 1})
        self.assertEqual(report["search_count"], 1)


if __name__ == "__main__":
    unittest.main()
