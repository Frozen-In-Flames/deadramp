"""Remainder additions — unit addition:collaboration-l3 (1 fork).

Traces to: ADDENDUM.md (this build) and UNION-SPEC.md. The addition
(Microsoft 365 Government Community Cloud & Supporting Services) was
spec'd under the group's EXISTING 21-family taxonomy applied
verbatim — AST-parsed out of the shipped scratch/extract.py by
scratch/additions_extract.py, never re-tuned. These tests pin the
spec outcome literally and exercise the fork against the substrate
its claim maps to, at the High baseline.

Claim outcome (pinned below): MSO365MTA 1 claim (messaging_chat) —
1 new claim, group total 49 -> 50, sheets 17 -> 18, forks carrying
at least one claim 13 -> 14. The description is suite-level boundary
prose of exactly the kind UNION-SPEC.md describes for this group:
its first sentence names messaging as a primary service (the claim,
and the census citation), and the remaining sentences tag nothing —
"collaboration services" is not a workspaces phrase, and the fork's
one named surface with no family at all, collaborative continuous
monitoring, is registered as a new gap in ADDENDUM.md section 5.
"""

import json
import os
import unittest

from collab_helpers import (
    AUDITOR,
    MEMBER,
    OUTSIDER,
    VIEWER,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)
from collab.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

UNIT_ID = "addition:collaboration-l3"
UNIT_FORK_IDS = ["MSO365MTA"]

EXPECTED_CLAIMS = {
    "MSO365MTA": ["messaging_chat"],  # Microsoft 365 GCC
}

# Families the addition does not claim (the complement of
# EXPECTED_CLAIMS over the group's 21-family taxonomy).
ADDITIONS_UNCLAIMED_FAMILIES = {
    "meetings_video", "voice_contact", "file_sharing", "workspaces",
    "whiteboard_visual", "calendaring", "presence", "task_work",
    "workflow", "esignature", "notifications", "search",
    "ai_assistance", "api_integration", "access_control", "audit",
    "encryption", "records_governance", "learning", "knowledge",
}


def _load_specs():
    with open(os.path.join(_GROUP_ROOT, "specs", "specs.json")) as fh:
        return json.load(fh)


def _load_raw_products():
    with open(os.path.join(_REPO_ROOT, "raw", "data_dump.json")) as fh:
        dump = json.load(fh)
    products = dump[3]["data"]["fedRAMPData"]["data"]["Products"]
    return {p["id"]: p for p in products}


class TestAdditionsSpecIntegrity(unittest.TestCase):
    """ADDENDUM section 1/2: membership, order, literal claim table,
    verbatim evidence, census citation, near-miss pins."""

    @classmethod
    def setUpClass(cls):
        cls.specs = _load_specs()
        cls.by_id = {s["fork_id"]: s for s in cls.specs}
        cls.raw = _load_raw_products()

    def test_sheet_count_and_unit_order(self):
        """17 original sheets + 1 appended in unit order = 18."""
        self.assertEqual(len(self.specs), 18)
        self.assertEqual(
            [s["fork_id"] for s in self.specs[17:]], UNIT_FORK_IDS)

    def test_membership_matches_remainder_unit(self):
        """The appended fork id is exactly the census unit's."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            units = json.load(fh)["build_units"]
        unit = next(u for u in units if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], UNIT_FORK_IDS)
        self.assertEqual(
            {s["fork_id"] for s in self.specs[17:]},
            set(unit["fork_ids"]))

    def test_literal_claim_table(self):
        """The fork's claimed families, exactly as spec'd."""
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)

    def test_additions_unclaimed_family_set(self):
        """The addition claims no family in the pinned unclaimed set
        (20 of the group's 21 families)."""
        claimed = {c["function_id"]
                   for c in self.by_id["MSO365MTA"]["functions_claimed"]}
        self.assertTrue(ADDITIONS_UNCLAIMED_FAMILIES.isdisjoint(claimed))
        self.assertEqual(len(claimed), 1)

    def test_group_claim_total(self):
        """49 original claims + 1 new = 50 across 18 sheets, with
        14 of 18 forks carrying at least one claim."""
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in self.specs), 50)
        self.assertEqual(
            sum(1 for s in self.specs if s["functions_claimed"]), 14)

    def test_evidence_is_verbatim_description_text(self):
        """The claim's evidence is a substring of the fork's own
        description."""
        sheet = self.by_id["MSO365MTA"]
        for claim in sheet["functions_claimed"]:
            self.assertIn(claim["evidence"], sheet["description"])

    def test_description_equals_cached_source(self):
        """The sheet description is the cached service_desc,
        stripped, exactly as the original pass recorded them."""
        expected = (self.raw["MSO365MTA"].get("service_desc")
                    or "").strip()
        self.assertEqual(
            self.by_id["MSO365MTA"]["description"], expected)

    def test_census_citation_verifies_and_is_the_claim(self):
        """The fork's single census citation verifies verbatim and
        is the very sentence the messaging claim rests on — the
        census classified this fork on its stated primary services,
        and the taxonomy tags the same sentence."""
        with open(os.path.join(
                _REPO_ROOT, "remainder", "class_all.json")) as fh:
            census = {c["fork_id"]: c for c in json.load(fh)}
        cites = census["MSO365MTA"]["citations"]
        self.assertEqual(len(cites), 1)
        sheet = self.by_id["MSO365MTA"]
        self.assertIn(cites[0], sheet["description"])
        self.assertEqual(
            sheet["functions_claimed"][0]["evidence"], cites[0])

    def test_near_misses_pinned(self):
        """Family-adjacent wording is present and still tags
        nothing: 'collaboration services' is not a workspaces
        phrase ('services' is not among the family's nouns);
        'streamlined communication' is not voice_contact;
        'comprehensive security' carries no access-control phrase
        and 'encrypt' never appears; 'IaaS/PaaS' does not fire the
        ai_assistance word-boundary pattern; 'collaborative
        continuous monitoring' has no family at all (new gap)."""
        sheet = self.by_id["MSO365MTA"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        desc = sheet["description"]
        self.assertIn("messaging and collaboration services", desc)
        self.assertNotIn("workspaces", claimed)
        self.assertIn("streamlined communication", desc)
        self.assertNotIn("voice_contact", claimed)
        self.assertIn("comprehensive security", desc)
        self.assertNotIn("access_control", claimed)
        self.assertNotIn("encrypt", desc.lower())
        self.assertNotIn("encryption", claimed)
        self.assertIn("IaaS/PaaS", desc)
        self.assertNotIn("ai_assistance", claimed)
        self.assertIn("collaborative continuous monitoring", desc)

    def test_sheet_fields_recorded_as_source(self):
        """Registry fields are the source's own values, recorded
        as-is: impact High, status FedRAMP In Process, and an empty
        service_model list (the source publishes none for this
        record — the sheet does not invent 'SaaS' from the product
        name). deployment_model is the source's 'Public Cloud',
        verbatim, despite the product name's 'Government Community
        Cloud'."""
        sheet = self.by_id["MSO365MTA"]
        self.assertEqual(sheet["fedramp_impact_level"], "High")
        self.assertEqual(
            sheet["authorization_status"], "FedRAMP In Process")
        self.assertEqual(sheet["service_model"], [])
        self.assertEqual(sheet["deployment_model"], "Public Cloud")
        self.assertEqual(sheet["cmmc_tier"], "L3-adjacent")


class TestAdditionsSubstrate(unittest.TestCase):
    """The addition fork exercised against the Core its claim maps
    to, at the High baseline (ADDENDUM section 3: core delta zero —
    messaging already had a disposition and a records form)."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_m365_messaging_at_high_baseline(self):
        """MSO365MTA claim -> Core 2: a channel message mentioning a
        member notifies them (kind mention); a shared file's list
        view carries NO content (opaque-reference discipline); and
        the High-baseline audit trail records the activity on a
        hash chain that verifies end to end (AU-9) and reduces by
        actor/action query (AU-7)."""
        channel = make_channel(self.store, self.ws_id, name="gcc-suite")
        msg = post_sample_message(
            self.store, self.ws_id, channel["id"],
            text="gcc rollout notes @carol", actor=MEMBER)
        carol_notes = self.store.notifications_for(VIEWER.name)
        self.assertTrue(any(
            n["kind"] == "mention" and n["ref_id"] == msg["id"]
            for n in carol_notes))
        rec = share_sample_file(
            self.store, self.ws_id, name="gcc-brief.txt",
            content="gcc briefing body")
        self.assertEqual(rec["version"], 1)
        listed = self.store.list_files(self.ws_id, MEMBER)
        self.assertNotIn("content", listed[0])  # contents stay opaque
        audit = self.store.audit
        self.assertEqual(audit.verify_chain(), (True, None))
        hits = audit.query(actor=MEMBER.name, action="message_post")
        self.assertTrue(any(e["target"] == msg["id"] for e in hits))
        # The auditor demo identity's trail is the same chain.
        self.assertEqual(AUDITOR.role, "auditor")

    def test_m365_membership_boundary(self):
        """MSO365MTA claim -> Core 1/10: the workspace boundary
        holds for the addition's surface — a non-member cannot post
        into the suite workspace. This is the additions case
        designed to trip under the group's signature membership
        drill (see tests/README.md)."""
        channel = make_channel(self.store, self.ws_id, name="suite")
        with self.assertRaises(PermissionDenied):
            post_sample_message(
                self.store, self.ws_id, channel["id"],
                text="outsider join attempt", actor=OUTSIDER)
        self.assertEqual(
            self.store.list_messages(self.ws_id, channel["id"], MEMBER),
            [])


if __name__ == "__main__":
    unittest.main()
