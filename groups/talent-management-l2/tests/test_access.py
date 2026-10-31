"""Core 13 (access side): the eleven-action permission matrix.

Traces to: UNION-SPEC.md "Implementation contract" (access.py) and
the AC control family — admin holds all eleven actions, member all
except org_write and audit_read, viewer exactly {org_read,
report_read}; unknown roles and actions are denied.
"""

import unittest

import talentmgmt_helpers as H
from talentmgmt.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from talentmgmt.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """The permission matrix is exactly the contract's matrix."""

    def test_eleven_actions(self):
        """Access: the action vocabulary is the contract's eleven."""
        self.assertEqual(len(ACTIONS), 11)
        self.assertEqual(set(ACTIONS), {
            "org_read", "org_write", "candidate_write",
            "requisition_write", "pipeline_write", "event_write",
            "assessment_write", "interview_write", "registry_write",
            "report_read", "audit_read",
        })

    def test_admin_holds_all(self):
        """Access: admin's set is the whole vocabulary."""
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))
        for action in ACTIONS:
            self.assertTrue(can(H.ADMIN, action), action)

    def test_member_holds_all_but_two(self):
        """Access: member lacks exactly org_write and audit_read."""
        self.assertEqual(PERMISSIONS["member"],
                         set(ACTIONS) - {"org_write", "audit_read"})
        self.assertFalse(can(H.MEMBER, "org_write"))
        self.assertFalse(can(H.MEMBER, "audit_read"))
        self.assertTrue(can(H.MEMBER, "pipeline_write"))

    def test_viewer_reads_only(self):
        """Access: viewer's set is exactly {org_read, report_read}."""
        self.assertEqual(PERMISSIONS["viewer"], {"org_read", "report_read"})
        self.assertFalse(can(H.VIEWER, "candidate_write"))

    def test_permissions_for_returns_a_copy(self):
        """Access: mutating the returned set does not corrupt the matrix."""
        granted = permissions_for("member")
        granted.clear()
        self.assertTrue(can(H.MEMBER, "pipeline_write"))

    def test_unknown_role_denied(self):
        """Access: an unknown role cannot construct a User, and
        permissions_for raises PermissionDenied."""
        with self.assertRaises(PermissionDenied):
            User("mallory", "superuser")
        with self.assertRaises(PermissionDenied):
            permissions_for("superuser")

    def test_require_and_unknown_action(self):
        """Access: require passes for a held action, raises for an
        unheld one, and an unknown action is never permitted."""
        require(H.MEMBER, "event_write")
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "event_write")
        self.assertFalse(can(H.ADMIN, "teleport"))
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "teleport")


if __name__ == "__main__":
    unittest.main()
