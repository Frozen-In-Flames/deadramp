"""Core 18 (access control): the eleven-action permission matrix.

Traces to: UNION-SPEC.md implementation contract for
``contractmgmt/access.py`` and the AC / IA control families.
"""

import unittest

import contractmgmt_helpers as H
from contractmgmt.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from contractmgmt.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """The exact permission matrix from the contract."""

    def test_eleven_actions(self):
        """Contract: the action set is exactly the eleven named actions."""
        self.assertEqual(len(ACTIONS), 11)
        self.assertEqual(
            set(ACTIONS),
            {
                "org_read", "org_write", "contract_write",
                "compliance_write", "case_write", "comm_write",
                "portal_write", "payment_write", "registry_write",
                "report_read", "audit_read",
            },
        )

    def test_admin_has_all(self):
        """AC-6: admin holds all eleven actions."""
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))
        for action in ACTIONS:
            self.assertTrue(can(H.ADMIN, action), action)

    def test_member_lacks_org_write_and_audit_read(self):
        """AC-6: member holds all except org_write and audit_read."""
        self.assertEqual(
            PERMISSIONS["member"], set(ACTIONS) - {"org_write", "audit_read"})
        self.assertFalse(can(H.MEMBER, "org_write"))
        self.assertFalse(can(H.MEMBER, "audit_read"))
        self.assertTrue(can(H.MEMBER, "contract_write"))

    def test_viewer_reads_only(self):
        """AC-6: viewer holds exactly {org_read, report_read}."""
        self.assertEqual(PERMISSIONS["viewer"], {"org_read", "report_read"})
        for action in ACTIONS:
            self.assertEqual(can(H.VIEWER, action),
                             action in ("org_read", "report_read"), action)

    def test_require_raises_for_denied(self):
        """require() raises PermissionDenied for a denied action."""
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "contract_write")
        require(H.ADMIN, "audit_read")  # does not raise

    def test_unknown_role_and_action_denied(self):
        """IA-2 hooks: unknown roles cannot be constructed; unknown
        actions are never permitted."""
        with self.assertRaises(PermissionDenied):
            User("mallory", "superuser")
        with self.assertRaises(PermissionDenied):
            permissions_for("superuser")
        self.assertFalse(can(H.ADMIN, "teleport"))
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "teleport")

    def test_permissions_for_returns_a_copy(self):
        """Mutating the returned set does not change the matrix."""
        granted = permissions_for("viewer")
        granted.add("audit_read")
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])


if __name__ == "__main__":
    unittest.main()
