"""Core: Access control (RBAC). Traces to UNION-SPEC core function 12
and control families AC-2/AC-3/AC-6, IA-2 (hooks)."""

import unittest

import grants_helpers as H
from grants.access import PERMISSIONS, ROLES, User, can, permissions_for, require
from grants.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    def test_roles_are_exactly_admin_member_viewer(self):
        self.assertEqual(set(ROLES), {"admin", "member", "viewer"})
        self.assertEqual(set(PERMISSIONS), {"admin", "member", "viewer"})

    def test_admin_holds_every_action(self):
        for action in ("read", "create_program", "enter", "decide", "record",
                       "manage_members", "audit_read", "admin"):
            self.assertIn(action, PERMISSIONS["admin"])

    def test_member_actions(self):
        self.assertEqual(
            PERMISSIONS["member"],
            {"read", "create_program", "enter", "decide", "record"},
        )

    def test_viewer_is_read_only(self):
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_audit_read_is_admin_only(self):
        self.assertNotIn("audit_read", PERMISSIONS["member"])
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_can_and_permissions_for(self):
        self.assertTrue(can(H.MEMBER, "decide"))
        self.assertFalse(can(H.VIEWER, "decide"))
        self.assertFalse(can(None, "read"))
        self.assertEqual(permissions_for("no-such-role"), set())

    def test_require_rejects_unknowns(self):
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("x", "no-such-role"), "read")
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "record")
        self.assertTrue(require(H.ADMIN, "audit_read"))


if __name__ == "__main__":
    unittest.main()
