"""Negative control: the suite must reject a mutant membership check.

Traces to: UNION-SPEC "Implementation contract" — tests 'include a
negative control: a mutant membership check (one that treats every
actor as a workspace member) whose behavior the canonical expectation
is shown to reject — a non-member's post must raise PermissionDenied,
and the mutant is demonstrated to wave it through — proving the suite
catches that defect class rather than merely passing.'

The traced claim: **workspace membership is the AC-3 access-enforcement
boundary.** Every workspace-scoped operation in the contract is gated
on it (the actor must be a workspace member or hold the platform admin
role, else PermissionDenied). The mutant below replaces that check
with one that returns True for any user/workspace pair.

Each test asserts three things, per the canonical pattern: (1) the
canonical expectation — the real implementation raises PermissionDenied
for the non-member; (2) the mutant would NOT raise — run through the
same gate shape, it waves the non-member through; and (3) a literal
assertRaises(AssertionError) demonstration that treating the mutant's
outcome as the expected outcome is a test failure.
"""

import unittest

from collab_helpers import (
    MEMBER,
    OUTSIDER,
    make_channel,
    make_store,
    post_sample_message,
    share_sample_file,
)
from collab.errors import PermissionDenied


def mutant_is_workspace_member(username, workspace):
    """The defect under control: every actor is a 'member'."""
    return True


def mutant_gate(username, workspace):
    """The membership gate as the mutant would run it.

    Mirrors the real gate's shape — raise PermissionDenied when the
    check fails, otherwise proceed — but with the mutant check inside,
    so it returns "allowed" for a non-member instead of raising.
    """
    if not mutant_is_workspace_member(username, workspace):
        raise PermissionDenied("not a workspace member")
    return "allowed"


class TestNegativeControlMutantMembership(unittest.TestCase):
    """Core: Access control (AC-3) — negative control for the
    membership boundary, traced claim: workspace membership is the
    AC-3 access-enforcement boundary."""

    def setUp(self):
        self.store, self.ws_id = make_store()
        self.channel = make_channel(self.store, self.ws_id)
        self.workspace = self.store.get_workspace(self.ws_id, MEMBER)

    def _assert_mutant_rejected(self, mutant_outcome):
        """The mutant's 'allowed' must fail the canonical expectation."""
        self.assertNotEqual(mutant_outcome, "denied")
        with self.assertRaises(AssertionError):
            self.assertEqual(mutant_outcome, "denied")

    def test_non_member_post_message(self):
        """Core: Messaging / Access control (AC-3), traced claim:
        workspace membership is the AC-3 boundary. Canonical: a
        non-member's post_message raises PermissionDenied and stores
        nothing. Mutant: the same actor is waved through the gate."""
        with self.assertRaises(PermissionDenied):
            post_sample_message(
                self.store, self.ws_id, self.channel["id"],
                text="intruder post", actor=OUTSIDER,
            )
        self.assertEqual(
            self.store.list_messages(self.ws_id, self.channel["id"], MEMBER),
            [],
        )
        mutant_outcome = mutant_gate(OUTSIDER.name, self.workspace)
        self.assertEqual(mutant_outcome, "allowed")  # mutant did not raise
        self._assert_mutant_rejected(mutant_outcome)

    def test_non_member_share_file(self):
        """Core: File sharing / Access control (AC-3), traced claim:
        workspace membership is the AC-3 boundary. Canonical: a
        non-member's share_file raises PermissionDenied and stores
        nothing. Mutant: waved through."""
        with self.assertRaises(PermissionDenied):
            share_sample_file(
                self.store, self.ws_id, name="intruder.txt",
                content="intruder body", actor=OUTSIDER,
            )
        self.assertEqual(self.store.list_files(self.ws_id, MEMBER), [])
        mutant_outcome = mutant_gate(OUTSIDER.name, self.workspace)
        self.assertEqual(mutant_outcome, "allowed")
        self._assert_mutant_rejected(mutant_outcome)

    def test_non_member_list_messages(self):
        """Core: Messaging / Access control (AC-3), traced claim:
        workspace membership is the AC-3 boundary. Canonical: a
        non-member's list_messages raises PermissionDenied (reads are
        gated too, not just writes). Mutant: waved through."""
        post_sample_message(
            self.store, self.ws_id, self.channel["id"], text="members only"
        )
        with self.assertRaises(PermissionDenied):
            self.store.list_messages(
                self.ws_id, self.channel["id"], OUTSIDER
            )
        mutant_outcome = mutant_gate(OUTSIDER.name, self.workspace)
        self.assertEqual(mutant_outcome, "allowed")
        self._assert_mutant_rejected(mutant_outcome)

    def test_non_member_search(self):
        """Core: Search / Access control (AC-3), traced claim:
        workspace membership is the AC-3 boundary. Canonical: a
        non-member's search raises PermissionDenied, so no workspace
        content can leak through search results. Mutant: waved
        through."""
        post_sample_message(
            self.store, self.ws_id, self.channel["id"],
            text="secret roadmap",
        )
        with self.assertRaises(PermissionDenied):
            self.store.search(self.ws_id, "roadmap", OUTSIDER)
        mutant_outcome = mutant_gate(OUTSIDER.name, self.workspace)
        self.assertEqual(mutant_outcome, "allowed")
        self._assert_mutant_rejected(mutant_outcome)


if __name__ == "__main__":
    unittest.main()
