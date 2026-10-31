"""Core function 11 (access control) / AC-2, AC-3, AC-6, IA-2 hooks.

The exact permission matrix from netmgmt.access, require()/can()
behavior for unknown users, roles, and actions.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.access import PERMISSIONS, ROLES, can, require
from netmgmt.errors import PermissionDenied


class TestPermissionMatrix(unittest.TestCase):
    def test_roles_are_exactly_admin_member_viewer(self):
        self.assertEqual(set(ROLES), {"admin", "member", "viewer"})
        self.assertEqual(set(PERMISSIONS), {"admin", "member", "viewer"})

    def test_admin_holds_every_action(self):
        self.assertEqual(
            PERMISSIONS["admin"],
            {"read", "create_org", "enter", "decide", "record",
             "manage_members", "audit_read", "admin"})

    def test_member_actions(self):
        self.assertEqual(
            PERMISSIONS["member"],
            {"read", "create_org", "enter", "decide", "record"})

    def test_viewer_is_read_only(self):
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_audit_read_is_admin_only(self):
        for user in (H.MEMBER, H.STAFF, H.VIEWER):
            self.assertFalse(can(user, "audit_read"))
            with self.assertRaises(PermissionDenied):
                require(user, "audit_read")
        self.assertTrue(can(H.ADMIN, "audit_read"))

    def test_require_rejects_none_and_unknown(self):
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        from netmgmt.access import User
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "teleport")

    def test_string_actor_has_no_role(self):
        # String actors carry identity only; role checks are skipped
        # in the store for them by design (service layer enforces).
        self.assertFalse(can("bob", "read"))


if __name__ == "__main__":
    unittest.main()
