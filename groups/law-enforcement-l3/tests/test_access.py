"""Access control (RBAC).

Traces to: Core 10 (Access control) and the AC / IA control families
in UNION-SPEC.md -- the exact permission matrix for
admin/member/viewer over the contract's nine actions, plus the
[L3] auditor role (AC-5): ``audit_read`` and nothing else.
"""

import unittest

from lawenf.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from lawenf.errors import PermissionDenied
from lawenf_helpers import ADMIN, AUDITOR, MEMBER, VIEWER


class TestAccessMatrix(unittest.TestCase):
    """Core 10: the permission matrix is exact, per the contract."""

    def test_admin_has_all_actions(self):
        self.assertEqual(permissions_for("admin"), set(ACTIONS))
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))

    def test_member_has_all_except_audit_read(self):
        self.assertEqual(permissions_for("member"), set(ACTIONS) - {"audit_read"})

    def test_viewer_reads_only(self):
        self.assertEqual(permissions_for("viewer"), {"matter_read", "report_read"})

    def test_auditor_has_audit_read_only(self):
        # [L3] AC-5: audit review is a duty separable from every
        # registry permission; the auditor holds exactly one action.
        self.assertEqual(permissions_for("auditor"), {"audit_read"})
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})
        self.assertTrue(can(AUDITOR, "audit_read"))
        for action in ACTIONS:
            if action != "audit_read":
                self.assertFalse(can(AUDITOR, action), action)
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "matter_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "matter_write")

    def test_can_and_require(self):
        self.assertTrue(can(MEMBER, "document_write"))
        self.assertFalse(can(MEMBER, "audit_read"))
        self.assertFalse(can(VIEWER, "source_write"))
        self.assertTrue(can(ADMIN, "audit_read"))
        require(ADMIN, "audit_read")  # does not raise
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "matter_write")
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "audit_read")

    def test_unknown_role_and_action_denied(self):
        with self.assertRaises(PermissionDenied):
            User("x", "superuser")
        with self.assertRaises(PermissionDenied):
            permissions_for("superuser")
        self.assertFalse(can(ADMIN, "teleport"))
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")

    def test_permissions_for_returns_a_copy(self):
        got = permissions_for("viewer")
        got.add("audit_read")
        self.assertNotIn("audit_read", permissions_for("viewer"))


if __name__ == "__main__":
    unittest.main()
