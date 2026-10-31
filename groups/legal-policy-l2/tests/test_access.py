"""Access control (RBAC).

Traces to: Core function 13 (Access control & audit) and the AC / IA
control families in UNION-SPEC.md — the exact permission matrix for
admin/member/viewer over the contract's eleven actions:
admin = all eleven; member = all except agency_write and audit_read;
viewer = {agency_read, report_read}. audit_read is admin-only.
"""

import unittest

import legalpol_helpers as H
from legalpol.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from legalpol.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 13 / AC: the permission matrix is exact, per the contract."""

    def test_eleven_actions(self):
        """Core 13: the contract names exactly eleven actions."""
        self.assertEqual(len(ACTIONS), 11)
        self.assertEqual(set(ACTIONS), {
            "agency_read", "agency_write", "workspace_write",
            "session_write", "library_write", "search_write",
            "document_write", "usage_write", "export", "report_read",
            "audit_read",
        })

    def test_admin_has_all_actions(self):
        """Core 13: admin holds all eleven, including audit_read."""
        self.assertEqual(permissions_for("admin"), set(ACTIONS))
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))

    def test_member_has_all_except_agency_write_and_audit_read(self):
        """Core 13: member = all except agency_write and audit_read."""
        self.assertEqual(
            permissions_for("member"),
            set(ACTIONS) - {"agency_write", "audit_read"})

    def test_viewer_reads_only(self):
        """Core 13: viewer = {agency_read, report_read}."""
        self.assertEqual(permissions_for("viewer"),
                         {"agency_read", "report_read"})

    def test_can_and_require(self):
        """Core 13 / AC-3: can() and require() enforce the matrix."""
        self.assertTrue(can(H.MEMBER, "session_write"))
        self.assertTrue(can(H.MEMBER, "export"))
        self.assertFalse(can(H.MEMBER, "agency_write"))
        self.assertFalse(can(H.MEMBER, "audit_read"))
        self.assertFalse(can(H.VIEWER, "workspace_write"))
        self.assertTrue(can(H.ADMIN, "audit_read"))
        require(H.ADMIN, "audit_read")  # does not raise
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "session_write")
        with self.assertRaises(PermissionDenied):
            require(H.MEMBER, "audit_read")

    def test_unknown_role_and_action_denied(self):
        """Core 13 / IA: unknown roles and actions are denied."""
        with self.assertRaises(PermissionDenied):
            User("x", "superuser")
        with self.assertRaises(PermissionDenied):
            permissions_for("superuser")
        self.assertFalse(can(H.ADMIN, "teleport"))
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "teleport")

    def test_permissions_for_returns_a_copy(self):
        """Core 13: mutating the returned set does not widen access."""
        got = permissions_for("viewer")
        got.add("audit_read")
        self.assertNotIn("audit_read", permissions_for("viewer"))


if __name__ == "__main__":
    unittest.main()
