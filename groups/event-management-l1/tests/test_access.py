"""Core function 12 (access half): the role/permission matrix.

Traces to AC-2/AC-3 at the Low baseline: three fixed roles, an
explicit permission set per role, unknown roles and actions denied.
"""

import unittest

from events.access import PERMISSIONS, User, can, permissions_for, require
from events.errors import PermissionDenied

from events_helpers import ADMIN, MEMBER, VIEWER


class AccessTests(unittest.TestCase):
    def test_admin_has_every_action(self):
        self.assertEqual(permissions_for("admin"),
                         {"read", "register", "manage", "outreach",
                          "matchmake", "audit_read", "admin"})

    def test_member_actions(self):
        self.assertEqual(permissions_for("member"),
                         {"read", "register", "manage", "outreach",
                          "matchmake"})

    def test_viewer_is_read_only(self):
        self.assertEqual(permissions_for("viewer"), {"read"})

    def test_unknown_role_has_no_permissions(self):
        self.assertEqual(permissions_for("root"), set())
        self.assertEqual(permissions_for(None), set())

    def test_can_and_require(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(MEMBER, "matchmake"))
        self.assertFalse(can(VIEWER, "manage"))
        self.assertFalse(can(None, "read"))
        self.assertTrue(require(MEMBER, "outreach"))

    def test_require_denies(self):
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "register")
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "root"), "read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(PermissionDenied):
            require(None, "read")

    def test_matrix_is_closed(self):
        for role, actions in PERMISSIONS.items():
            self.assertIn(role, ("admin", "member", "viewer"))
            for action in actions:
                self.assertIn(action, ("read", "register", "manage",
                                       "outreach", "matchmake",
                                       "audit_read", "admin"))


if __name__ == "__main__":
    unittest.main()
