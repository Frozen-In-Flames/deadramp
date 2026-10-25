"""Search & discovery tests.

Traces to: UNION-SPEC Core function 7 (Search — literal,
case-insensitive substring search across a workspace's messages, file
names, event titles, and board cards) / ranking row 15 (Search &
discovery, 7 siblings); Implementation contract for
``collab/store.py`` search; control families AC-3 (search results are
scoped to the one workspace — never across workspaces) and the spec's
plain statement that Core search is literal substring matching, not
semantic/AI search.
"""

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

SEARCH_KEYS = {"messages", "files", "events", "cards"}


class SearchBase(unittest.TestCase):
    """Two workspaces whose objects share one term and differ elsewhere.

    Workspace 1 (the fixture): a message, file, event and card all
    carrying the word "report". Workspace 2 (dave's): objects carrying
    "report" too, plus a unique term "zebra" that exists nowhere in
    workspace 1 — the leak canary.
    """

    def setUp(self):
        self.store, self.ws_id = make_store()
        channel = make_channel(self.store, self.ws_id)
        self.message = post_sample_message(
            self.store, self.ws_id, channel["id"],
            text="Quarterly Report is ready",
        )
        self.file = share_sample_file(
            self.store, self.ws_id, name="Report-2026.txt",
            content="numbers",
        )
        self.event = create_sample_event(
            self.store, self.ws_id, title="Report review"
        )
        board = create_sample_board(self.store, self.ws_id)
        self.card = add_sample_card(
            self.store, self.ws_id, board["id"], text="report card"
        )

        self.other_ws = self.store.create_workspace("dave-space", OUTSIDER)
        other_channel = make_channel(
            self.store, self.other_ws["id"], actor=OUTSIDER
        )
        self.other_message = post_sample_message(
            self.store, self.other_ws["id"], other_channel["id"],
            text="zebra report from the other workspace", actor=OUTSIDER,
        )
        self.other_file = share_sample_file(
            self.store, self.other_ws["id"], name="zebra-report.txt",
            content="other", actor=OUTSIDER,
        )
        self.other_event = create_sample_event(
            self.store, self.other_ws["id"], title="zebra report sync",
            actor=OUTSIDER,
        )
        other_board = create_sample_board(
            self.store, self.other_ws["id"], actor=OUTSIDER
        )
        self.other_card = add_sample_card(
            self.store, self.other_ws["id"], other_board["id"],
            text="zebra report card", actor=OUTSIDER,
        )


class TestSearchMatches(SearchBase):
    """Core: Search — what matches, and how."""

    def test_search_returns_the_four_result_buckets(self):
        """Core: Search. Contract: search returns {messages, files,
        events, cards}."""
        result = self.store.search(self.ws_id, "report", MEMBER)
        self.assertEqual(set(result.keys()), SEARCH_KEYS)
        for bucket in result.values():
            self.assertIsInstance(bucket, list)

    def test_search_finds_a_message_by_substring(self):
        """Core: Search. Message text is searched by literal
        substring."""
        result = self.store.search(self.ws_id, "Quarterly", MEMBER)
        self.assertEqual(
            [m["id"] for m in result["messages"]], [self.message["id"]]
        )

    def test_search_finds_a_file_by_name_substring(self):
        """Core: Search. File *names* are searched (here a mid-name
        substring)."""
        result = self.store.search(self.ws_id, "2026", MEMBER)
        self.assertEqual([f["id"] for f in result["files"]], [self.file["id"]])

    def test_search_finds_an_event_by_title_substring(self):
        """Core: Search. Event titles are searched by substring."""
        result = self.store.search(self.ws_id, "review", MEMBER)
        self.assertEqual(
            [e["id"] for e in result["events"]], [self.event["id"]]
        )

    def test_search_finds_a_card_by_text_substring(self):
        """Core: Search. Board card text is searched by substring."""
        result = self.store.search(self.ws_id, "card", MEMBER)
        self.assertEqual([c["id"] for c in result["cards"]], [self.card["id"]])

    def test_search_is_case_insensitive(self):
        """Core: Search. Contract: matching is case-insensitive in the
        query and in the content alike."""
        for query in ("REPORT", "Report", "rEpOrT"):
            with self.subTest(query=query):
                result = self.store.search(self.ws_id, query, MEMBER)
                self.assertEqual(len(result["messages"]), 1)
                self.assertEqual(len(result["files"]), 1)
                self.assertEqual(len(result["events"]), 1)
                self.assertEqual(len(result["cards"]), 1)

    def test_search_matches_mid_word_substrings(self):
        """Core: Search. Literal substring, not word matching: 'port'
        matches 'Report' everywhere it occurs."""
        result = self.store.search(self.ws_id, "port", MEMBER)
        self.assertEqual(len(result["messages"]), 1)
        self.assertEqual(len(result["files"]), 1)

    def test_search_with_no_match_returns_empty_buckets(self):
        """Core: Search. A query matching nothing returns four empty
        lists, not an error."""
        result = self.store.search(self.ws_id, "no-such-term-xyz", MEMBER)
        self.assertEqual(
            result, {"messages": [], "files": [], "events": [], "cards": []}
        )

    def test_viewer_member_may_search(self):
        """Core: Search + Access control. Search requires read, which
        viewer holds."""
        result = self.store.search(self.ws_id, "report", VIEWER)
        self.assertEqual(len(result["messages"]), 1)


class TestSearchWorkspaceScoping(SearchBase):
    """Core: Search (AC-3) — results never leak another workspace."""

    def test_term_unique_to_another_workspace_finds_nothing_here(self):
        """Core: Search (AC-3). CRITICAL: 'zebra' exists in workspace
        2's message, file, event and card — searching workspace 1 for
        it returns four empty buckets."""
        result = self.store.search(self.ws_id, "zebra", MEMBER)
        self.assertEqual(
            result, {"messages": [], "files": [], "events": [], "cards": []}
        )

    def test_shared_term_returns_only_this_workspaces_objects(self):
        """Core: Search (AC-3). CRITICAL: 'report' exists in both
        workspaces; workspace 1's results contain workspace 1's objects
        only — every returned dict is scoped to workspace 1 and no
        workspace-2 id appears."""
        result = self.store.search(self.ws_id, "report", MEMBER)
        other_ids = {
            self.other_message["id"], self.other_file["id"],
            self.other_event["id"], self.other_card["id"],
        }
        for bucket in ("messages", "files", "events", "cards"):
            for item in result[bucket]:
                with self.subTest(bucket=bucket, item=item["id"]):
                    self.assertEqual(item["workspace_id"], self.ws_id)
                    self.assertNotIn(item["id"], other_ids)
        self.assertEqual(
            [m["id"] for m in result["messages"]], [self.message["id"]]
        )
        self.assertEqual(
            [f["id"] for f in result["files"]], [self.file["id"]]
        )
        self.assertEqual(
            [e["id"] for e in result["events"]], [self.event["id"]]
        )
        self.assertEqual([c["id"] for c in result["cards"]], [self.card["id"]])

    def test_searching_the_other_workspace_returns_its_objects(self):
        """Core: Search (AC-3). Scoping is symmetric: workspace 2's
        owner finds the zebra objects there, and only there."""
        result = self.store.search(self.other_ws["id"], "zebra", OUTSIDER)
        self.assertEqual(
            [m["id"] for m in result["messages"]], [self.other_message["id"]]
        )
        self.assertEqual(
            [f["id"] for f in result["files"]], [self.other_file["id"]]
        )

    def test_non_member_cannot_search_the_workspace(self):
        """Core: Search (AC-3). Search itself enforces membership: a
        non-member is denied before any result exists."""
        with self.assertRaises(PermissionDenied):
            self.store.search(self.ws_id, "report", OUTSIDER)


if __name__ == "__main__":
    unittest.main()
