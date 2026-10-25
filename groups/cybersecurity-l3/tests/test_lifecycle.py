"""Finding-lifecycle tests.

Traces to: UNION-SPEC Core function 3 (Finding triage & lifecycle —
findings move through a fixed lifecycle with assignment; invalid
transitions are rejected, never silently applied); Implementation
contract for ``cyber/store.py`` FINDING_STATUSES /
FINDING_TRANSITIONS, transition_finding and assign_finding; control
families IR-4 / IR-5.
"""

import unittest

from cyber_helpers import ANALYST, VIEWER, fresh_store, make_asset
from cyber_helpers import ingest_sample_finding
from cyber.errors import NotFoundError, PermissionDenied, ValidationError
from cyber.store import FINDING_TRANSITIONS

# Shortest legal path from "new" to each status, per FINDING_TRANSITIONS.
PATH_TO = {
    "new": [],
    "triaged": ["triaged"],
    "in_progress": ["triaged", "in_progress"],
    "mitigated": ["triaged", "in_progress", "mitigated"],
    "accepted": ["triaged", "accepted"],
    "false_positive": ["false_positive"],
    "closed": ["false_positive", "closed"],
}

ALLOWED = [
    ("new", "triaged"), ("new", "false_positive"),
    ("triaged", "in_progress"), ("triaged", "accepted"),
    ("triaged", "false_positive"),
    ("in_progress", "mitigated"), ("in_progress", "accepted"),
    ("mitigated", "closed"), ("mitigated", "in_progress"),
    ("accepted", "in_progress"), ("accepted", "closed"),
    ("false_positive", "closed"),
]

FORBIDDEN = [
    ("new", "in_progress"), ("new", "mitigated"), ("new", "accepted"),
    ("new", "closed"),
    ("triaged", "mitigated"), ("triaged", "closed"), ("triaged", "new"),
    ("in_progress", "triaged"), ("in_progress", "false_positive"),
    ("in_progress", "closed"), ("in_progress", "new"),
    ("mitigated", "triaged"), ("mitigated", "accepted"),
    ("mitigated", "false_positive"),
    ("accepted", "mitigated"), ("accepted", "triaged"),
    ("accepted", "false_positive"),
    ("false_positive", "in_progress"), ("false_positive", "triaged"),
    ("closed", "new"), ("closed", "triaged"), ("closed", "in_progress"),
    ("closed", "closed"),
]


class LifecycleBase(unittest.TestCase):
    """A fresh store with one asset; findings are driven per test."""

    def setUp(self):
        self.store = fresh_store()
        self.asset = make_asset(self.store)

    def finding_in(self, status):
        """Ingest a finding and drive it to ``status`` legally."""
        finding = ingest_sample_finding(self.store, self.asset["id"])
        for step in PATH_TO[status]:
            finding = self.store.transition_finding(
                finding["id"], step, actor=ANALYST
            )
        self.assertEqual(finding["status"], status)
        return finding


class TestTransitionMapShape(unittest.TestCase):
    """Core: Finding lifecycle — the published transition map itself."""

    def test_transition_map_matches_the_contract(self):
        """Core: Finding lifecycle. Contract: FINDING_TRANSITIONS is
        exactly {"new": {triaged, false_positive}, "triaged":
        {in_progress, accepted, false_positive}, "in_progress":
        {mitigated, accepted}, "mitigated": {closed, in_progress},
        "accepted": {in_progress, closed}, "false_positive":
        {closed}, "closed": set()}."""
        expected = {
            "new": {"triaged", "false_positive"},
            "triaged": {"in_progress", "accepted", "false_positive"},
            "in_progress": {"mitigated", "accepted"},
            "mitigated": {"closed", "in_progress"},
            "accepted": {"in_progress", "closed"},
            "false_positive": {"closed"},
            "closed": set(),
        }
        actual = {k: set(v) for k, v in FINDING_TRANSITIONS.items()}
        self.assertEqual(actual, expected)


class TestAllowedTransitions(LifecycleBase):
    """Core: Finding lifecycle — every allowed transition succeeds."""

    def test_every_allowed_transition_succeeds(self):
        """Core: Finding lifecycle. Contract: transition_finding
        accepts every (from, to) pair in FINDING_TRANSITIONS and
        returns the updated finding dict in the new status."""
        for source, target in ALLOWED:
            with self.subTest(source=source, target=target):
                finding = self.finding_in(source)
                updated = self.store.transition_finding(
                    finding["id"], target, actor=ANALYST
                )
                self.assertEqual(updated["status"], target)
                self.assertEqual(
                    self.store.get_finding(finding["id"], actor=ANALYST)
                    ["status"],
                    target,
                )

    def test_full_happy_path_new_to_closed(self):
        """Core: Finding lifecycle. The canonical handling record
        (IR-4): new → triaged → in_progress → mitigated → closed."""
        finding = self.finding_in("new")
        for step in ("triaged", "in_progress", "mitigated", "closed"):
            finding = self.store.transition_finding(
                finding["id"], step, actor=ANALYST
            )
        self.assertEqual(finding["status"], "closed")

    def test_mitigated_can_reopen_to_in_progress(self):
        """Core: Finding lifecycle. Contract: mitigated →
        in_progress is an allowed edge (a fix that regresses)."""
        finding = self.finding_in("mitigated")
        updated = self.store.transition_finding(
            finding["id"], "in_progress", actor=ANALYST
        )
        self.assertEqual(updated["status"], "in_progress")


class TestForbiddenTransitions(LifecycleBase):
    """Core: Finding lifecycle — forbidden transitions are rejected."""

    def test_representative_forbidden_transitions_are_rejected(self):
        """Core: Finding lifecycle. Contract: 'new_status must be in
        FINDING_TRANSITIONS[current], else ValidationError' — a
        representative forbidden set spanning every source status is
        rejected."""
        for source, target in FORBIDDEN:
            with self.subTest(source=source, target=target):
                finding = self.finding_in(source)
                with self.assertRaises(ValidationError):
                    self.store.transition_finding(
                        finding["id"], target, actor=ANALYST
                    )

    def test_closed_is_terminal(self):
        """Core: Finding lifecycle. Contract: FINDING_TRANSITIONS
        ["closed"] is the empty set — no status is reachable from
        closed."""
        finding = self.finding_in("closed")
        for target in ("new", "triaged", "in_progress", "mitigated",
                       "accepted", "false_positive", "closed"):
            with self.subTest(target=target):
                with self.assertRaises(ValidationError):
                    self.store.transition_finding(
                        finding["id"], target, actor=ANALYST
                    )

    def test_same_status_transition_is_rejected(self):
        """Core: Finding lifecycle. A transition to the current status
        is not in any transition set, so it is a ValidationError,
        never a silent no-op ('rejected, never silently applied')."""
        for status in ("new", "triaged", "in_progress", "mitigated",
                       "accepted", "false_positive"):
            with self.subTest(status=status):
                finding = self.finding_in(status)
                with self.assertRaises(ValidationError):
                    self.store.transition_finding(
                        finding["id"], status, actor=ANALYST
                    )

    def test_unknown_status_is_rejected(self):
        """Core: Finding lifecycle. Contract: 'new_status must be in
        FINDING_STATUSES ... else ValidationError' — a string outside
        the seven statuses is rejected."""
        finding = self.finding_in("new")
        with self.assertRaises(ValidationError):
            self.store.transition_finding(
                finding["id"], "doing", actor=ANALYST
            )

    def test_failed_transition_leaves_the_status_unchanged(self):
        """Core: Finding lifecycle. Contract: a failed operation
        'changes nothing' — after a rejected transition the finding is
        still in its prior status."""
        finding = self.finding_in("new")
        with self.assertRaises(ValidationError):
            self.store.transition_finding(
                finding["id"], "closed", actor=ANALYST
            )
        self.assertEqual(
            self.store.get_finding(finding["id"], actor=ANALYST)["status"],
            "new",
        )

    def test_transition_unknown_finding_is_not_found(self):
        """Core: Finding lifecycle. transition_finding on an unknown
        id raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.transition_finding(
                "find-999999", "triaged", actor=ANALYST
            )

    def test_viewer_cannot_transition(self):
        """Core: Finding lifecycle + Access control. transition_finding
        takes action triage, which viewer lacks."""
        finding = self.finding_in("new")
        with self.assertRaises(PermissionDenied):
            self.store.transition_finding(
                finding["id"], "triaged", actor=VIEWER
            )


class TestAssignFinding(LifecycleBase):
    """Core: Finding lifecycle — assign_finding / unassign."""

    def test_assign_sets_the_assignee(self):
        """Core: Finding lifecycle. Contract: assign_finding returns
        the updated finding dict with the given assignee."""
        finding = self.finding_in("new")
        self.assertIsNone(finding["assignee"])
        updated = self.store.assign_finding(
            finding["id"], "carol-analyst", actor=ANALYST
        )
        self.assertEqual(updated["assignee"], "carol-analyst")
        self.assertEqual(
            self.store.get_finding(finding["id"], actor=ANALYST)
            ["assignee"],
            "carol-analyst",
        )

    def test_unassign_with_none_clears_the_assignee(self):
        """Core: Finding lifecycle. Contract: assignee is 'a non-empty
        string or None (unassign)'."""
        finding = self.finding_in("new")
        self.store.assign_finding(finding["id"], "bob", actor=ANALYST)
        updated = self.store.assign_finding(
            finding["id"], None, actor=ANALYST
        )
        self.assertIsNone(updated["assignee"])

    def test_assign_empty_string_is_validation_error(self):
        """Core: Finding lifecycle. Contract: an assignee that is
        neither a non-empty string nor None is rejected."""
        finding = self.finding_in("new")
        with self.assertRaises(ValidationError):
            self.store.assign_finding(finding["id"], "", actor=ANALYST)
        self.assertIsNone(
            self.store.get_finding(finding["id"], actor=ANALYST)
            ["assignee"]
        )

    def test_assign_unknown_finding_is_not_found(self):
        """Core: Finding lifecycle. assign_finding on an unknown id
        raises NotFoundError."""
        with self.assertRaises(NotFoundError):
            self.store.assign_finding("find-999999", "bob", actor=ANALYST)

    def test_viewer_cannot_assign(self):
        """Core: Finding lifecycle + Access control. assign_finding
        takes action triage, which viewer lacks."""
        finding = self.finding_in("new")
        with self.assertRaises(PermissionDenied):
            self.store.assign_finding(finding["id"], "bob", actor=VIEWER)


if __name__ == "__main__":
    unittest.main()
