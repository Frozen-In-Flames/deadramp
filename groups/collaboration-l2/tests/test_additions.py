"""Remainder additions — unit addition:collaboration-l2 (3 forks).

Traces to: ADDENDUM.md (this build) and UNION-SPEC.md. The additions
(Cisco Webex for Government, Huddle, IdeaScale Gov) were spec'd under
the group's EXISTING 21-family taxonomy applied verbatim — parsed out
of the shipped scratch/extract.py via ast by
scratch/additions_extract.py, never re-tuned. These tests pin the
spec outcome literally and exercise each addition fork against the
substrate its claims map to.

Claim outcome (pinned below): Webex 7 claims, Huddle 4, IdeaScale 0 —
11 new claims, group total 222 -> 233. IdeaScale is a zero-claim
fork: both of its census citations verify as verbatim description
text yet tag no family (verification is not a claim), and its whole
described function — innovation management & crowdsourcing — has no
family in the taxonomy; it is registered as a new gap in ADDENDUM.md
section 5, not rounded into a claim here.
"""

import json
import os
import unittest

from collab_helpers import (
    MEMBER,
    OUTSIDER,
    VIEWER,
    add_sample_card,
    create_sample_board,
    create_sample_event,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)
from collab.errors import PermissionDenied

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_GROUP_ROOT = os.path.dirname(_TESTS_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_GROUP_ROOT))

UNIT_ID = "addition:collaboration-l2"
UNIT_FORK_IDS = ["F1511207635", "F1408115175", "F1512017638"]

EXPECTED_CLAIMS = {
    "F1511207635": [  # Cisco Webex for Government
        "messaging_chat", "meetings_video", "voice_contact",
        "file_sharing", "workspaces", "workflow", "ai_assistance",
    ],
    "F1408115175": [  # Huddle
        "workspaces", "api_integration", "audit", "records_governance",
    ],
    "F1512017638": [],  # IdeaScale Gov — zero-claim fork, pinned
}

# Families none of the 3 additions claim (the complement of the union
# of EXPECTED_CLAIMS over the group's 21-family taxonomy).
ADDITIONS_UNCLAIMED_FAMILIES = {
    "whiteboard_visual", "calendaring", "presence", "task_work",
    "esignature", "notifications", "search", "access_control",
    "encryption", "learning", "knowledge",
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
    verbatim evidence, census citations, near-miss pins."""

    @classmethod
    def setUpClass(cls):
        cls.specs = _load_specs()
        cls.by_id = {s["fork_id"]: s for s in cls.specs}
        cls.raw = _load_raw_products()

    def test_sheet_count_and_unit_order(self):
        """57 original sheets + 3 appended in unit order = 60."""
        self.assertEqual(len(self.specs), 60)
        self.assertEqual(
            [s["fork_id"] for s in self.specs[57:]], UNIT_FORK_IDS)

    def test_membership_matches_remainder_unit(self):
        """Appended fork ids are exactly the census unit's fork_ids."""
        with open(os.path.join(_REPO_ROOT, "remainder.json")) as fh:
            units = json.load(fh)["build_units"]
        unit = next(u for u in units if u["unit_id"] == UNIT_ID)
        self.assertEqual(unit["fork_ids"], UNIT_FORK_IDS)
        self.assertEqual(
            {s["fork_id"] for s in self.specs[57:]},
            set(unit["fork_ids"]))

    def test_literal_claim_table(self):
        """Per-fork claimed families, exactly as spec'd (ADDENDUM s.2)."""
        for fid, expected in EXPECTED_CLAIMS.items():
            got = [c["function_id"]
                   for c in self.by_id[fid]["functions_claimed"]]
            self.assertEqual(got, expected, fid)

    def test_additions_unclaimed_family_set(self):
        """No addition claims any family in the pinned unclaimed set."""
        claimed = set()
        for fid in UNIT_FORK_IDS:
            claimed |= {c["function_id"]
                        for c in self.by_id[fid]["functions_claimed"]}
        self.assertTrue(ADDITIONS_UNCLAIMED_FAMILIES.isdisjoint(claimed))
        self.assertEqual(len(claimed), 10)  # 21 families - 11 unclaimed

    def test_group_claim_total(self):
        """222 original claims + 11 new = 233 across 60 sheets."""
        self.assertEqual(
            sum(len(s["functions_claimed"]) for s in self.specs), 233)

    def test_evidence_is_verbatim_description_text(self):
        """Every claim's evidence is a substring of the fork's own
        description (modulo the extractor's 400-char truncation)."""
        for fid in UNIT_FORK_IDS:
            sheet = self.by_id[fid]
            for claim in sheet["functions_claimed"]:
                ev = claim["evidence"]
                if ev.endswith("..."):
                    self.assertIn(ev[:-3], sheet["description"], fid)
                else:
                    self.assertIn(ev, sheet["description"], fid)

    def test_descriptions_equal_cached_source(self):
        """Sheet descriptions are the cached service_desc, stripped,
        exactly as the original pass recorded them."""
        for fid in UNIT_FORK_IDS:
            expected = (self.raw[fid].get("service_desc") or "").strip()
            self.assertEqual(self.by_id[fid]["description"], expected, fid)

    def test_census_citations_verify_verbatim(self):
        """All 4 census citations are verbatim substrings of the
        forks' own descriptions — including IdeaScale's 2, which tag
        no family: verification is not a claim."""
        with open(os.path.join(
                _REPO_ROOT, "remainder", "class_all.json")) as fh:
            census = {c["fork_id"]: c for c in json.load(fh)}
        total = 0
        for fid in UNIT_FORK_IDS:
            for cite in census[fid]["citations"]:
                total += 1
                self.assertIn(cite, self.by_id[fid]["description"], fid)
        self.assertEqual(total, 4)

    def test_ideascale_zero_claims_pinned(self):
        """IdeaScale claims nothing; the near-miss wording is present
        in its description and still tags no family: 'collaboratively
        transform' is not a workspaces phrase and 'project plans' is
        not project management."""
        sheet = self.by_id["F1512017638"]
        self.assertEqual(sheet["functions_claimed"], [])
        desc = sheet["description"]
        self.assertIn("collaboratively transform", desc)
        self.assertIn("actionable project plans", desc)
        self.assertIn("crowdsourcing", desc)  # its function: a new gap

    def test_huddle_near_misses_pinned(self):
        """Huddle: 'trackable tasks' is not 'task tracking' (no
        task_work claim); 'control over who can access' is not an
        access_control phrase; and the file_sharing family never
        fires — 'File Sharing' lives in the product NAME, and the
        description says only 'documents'."""
        sheet = self.by_id["F1408115175"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        desc = sheet["description"]
        self.assertIn("trackable tasks and assignments", desc)
        self.assertNotIn("task_work", claimed)
        self.assertIn("who can access, view, and edit", desc)
        self.assertNotIn("access_control", claimed)
        self.assertIn("File Sharing", sheet["product"])
        self.assertNotIn("file sharing", desc.lower())
        self.assertNotIn("file_sharing", claimed)

    def test_huddle_api_integration_artifact_pinned(self):
        """Wording artifact, recorded not corrected: Huddle's
        api_integration evidence is the adjective use 'tightly
        integrated workspaces' (the family's integrat stem), not the
        later 'Integrations with Microsoft Office' sentence — the
        extractor stores the FIRST matching sentence, per house
        method."""
        sheet = self.by_id["F1408115175"]
        ev = next(c["evidence"] for c in sheet["functions_claimed"]
                  if c["function_id"] == "api_integration")
        self.assertIn("tightly integrated workspaces", ev)

    def test_webex_near_misses_and_artifacts_pinned(self):
        """Webex: 'scheduling portal' is not a calendaring phrase
        (no calendaring claim); 'encrypt' never appears (no
        encryption claim despite the 'secure' prose); the workflow
        claim's evidence is 'workflows at scale' — prose weight,
        recorded as an artifact in ADDENDUM section 2."""
        sheet = self.by_id["F1511207635"]
        claimed = {c["function_id"] for c in sheet["functions_claimed"]}
        desc = sheet["description"]
        self.assertIn("advanced scheduling portal", desc)
        self.assertNotIn("calendaring", claimed)
        self.assertNotIn("encrypt", desc.lower())
        self.assertNotIn("encryption", claimed)
        ev = next(c["evidence"] for c in sheet["functions_claimed"]
                  if c["function_id"] == "workflow")
        self.assertIn("workflows at scale", ev)


class TestAdditionsSubstrate(unittest.TestCase):
    """Each addition fork exercised against the Core its claims map
    to (ADDENDUM section 3: core delta zero — every claimed family
    already had a disposition and a records form)."""

    def setUp(self):
        self.store, self.ws_id = make_store()

    def test_webex_messaging_files_and_meeting_surface(self):
        """Webex claims -> Core 2/3/4: a channel message mentioning a
        member notifies them (kind mention); a shared file is a
        versioned metadata record — name, size, SHA-256 — whose list
        view carries NO content (opaque reference discipline); a
        meeting is calendared as an event record (the coordination
        surface is Core; media transport stays Extended)."""
        channel = make_channel(self.store, self.ws_id, name="webex-suite")
        msg = post_sample_message(
            self.store, self.ws_id, channel["id"],
            text="standup notes @carol", actor=MEMBER)
        self.assertEqual(msg["author"], MEMBER.name)
        carol_notes = self.store.notifications_for(VIEWER.name)
        self.assertTrue(any(
            n["kind"] == "mention" and n["ref_id"] == msg["id"]
            for n in carol_notes))
        rec = share_sample_file(
            self.store, self.ws_id, name="briefing.txt",
            content="webex briefing body")
        self.assertEqual(rec["version"], 1)
        self.assertEqual(rec["size_bytes"], len("webex briefing body"))
        self.assertEqual(len(rec["sha256"]), 64)
        listed = self.store.list_files(self.ws_id, MEMBER)
        self.assertNotIn("content", listed[0])  # contents stay opaque
        event = create_sample_event(
            self.store, self.ws_id, title="Webex meeting",
            attendees=[VIEWER.name])
        self.assertEqual(event["title"], "Webex meeting")

    def test_webex_workspace_membership_boundary(self):
        """Webex claims -> Core 1/10: the workspace boundary holds
        for the additions' surface — a non-member cannot post into
        the suite workspace. This is the additions case designed to
        trip under the group's signature membership drill (see
        tests/README.md)."""
        channel = make_channel(self.store, self.ws_id, name="suite")
        with self.assertRaises(PermissionDenied):
            post_sample_message(
                self.store, self.ws_id, channel["id"],
                text="outsider join attempt", actor=OUTSIDER)
        self.assertEqual(
            self.store.list_messages(self.ws_id, channel["id"], MEMBER),
            [])

    def test_huddle_versioned_files_audit_and_search(self):
        """Huddle claims -> Core 1/3/7/11: re-sharing a name creates
        the next version; the audit trail records the shares; literal
        search finds the file by name inside the workspace."""
        v1 = share_sample_file(
            self.store, self.ws_id, name="huddle-doc.txt", content="v1")
        v2 = share_sample_file(
            self.store, self.ws_id, name="huddle-doc.txt", content="v2!")
        self.assertEqual((v1["version"], v2["version"]), (1, 2))
        self.assertNotEqual(v1["sha256"], v2["sha256"])
        actions = [e["action"] for e in self.store.audit.entries()]
        self.assertEqual(actions.count("file_share"), 2)
        hits = self.store.search(self.ws_id, "huddle-doc", MEMBER)
        self.assertEqual(len(hits["files"]), 2)

    def test_ideascale_zero_claim_substrate_minimum(self):
        """IdeaScale claims nothing, so no Core slice is attributed
        to it; the case pins the substrate minimum every sibling
        presupposes (Core 1/10): its users' workspace exists, holds
        a board of positioned text cards (opaque input references),
        and the membership boundary denies an outsider's read."""
        board = create_sample_board(
            self.store, self.ws_id, name="idea-board")
        card = add_sample_card(
            self.store, self.ws_id, board["id"],
            text="idea: ref-2026-001", x=1, y=2)
        self.assertEqual(card["board_id"], board["id"])
        with self.assertRaises(PermissionDenied):
            self.store.list_cards(self.ws_id, board["id"], OUTSIDER)


if __name__ == "__main__":
    unittest.main()
