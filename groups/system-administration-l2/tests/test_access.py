"""Core 11 (Access control) / AC, IA: the exact permission matrix
and require() behavior, per UNION-SPEC.md.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.access import PERMISSIONS, User, can, require
from sysadmin.errors import PermissionDenied


class TestAccess(unittest.TestCase):
    def test_admin_matrix_exact(self):
        self.assertEqual(PERMISSIONS["admin"], {
            "read", "create_org", "enter", "decide", "record",
            "manage_members", "audit_read", "admin"})

    def test_member_matrix_exact(self):
        self.assertEqual(PERMISSIONS["member"], {
            "read", "create_org", "enter", "decide", "record"})

    def test_viewer_matrix_exact(self):
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_require_allows_and_denies(self):
        self.assertTrue(require(H.ADMIN, "audit_read"))
        self.assertTrue(require(H.MEMBER, "enter"))
        with self.assertRaises(PermissionDenied):
            require(H.MEMBER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "enter")

    def test_require_rejects_unknowns(self):
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "teleport")

    def test_can_mirrors_matrix(self):
        self.assertTrue(can(H.ADMIN, "manage_members"))
        self.assertFalse(can(H.VIEWER, "decide"))
        self.assertFalse(can(None, "read"))

    def test_audit_read_is_admin_only(self):
        for user in (H.MEMBER, H.STAFF, H.VIEWER, H.OUTSIDER):
            with self.assertRaises(PermissionDenied):
                require(user, "audit_read")


if __name__ == "__main__":
    unittest.main()
