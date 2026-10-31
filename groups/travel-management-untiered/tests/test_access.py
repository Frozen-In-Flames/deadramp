import unittest

from travel.access import PERMISSIONS, User, can, permissions_for, require
from travel.errors import PermissionDenied

from travel_helpers import ADMIN, MEMBER, VIEWER


class TestAccessMatrix(unittest.TestCase):
    def test_admin_has_all_actions(self):
        self.assertEqual(permissions_for("admin"), PERMISSIONS["admin"])
        for action in PERMISSIONS["admin"]:
            self.assertTrue(can(ADMIN, action))

    def test_member_actions(self):
        for action in ("read", "enter", "decide", "record"):
            self.assertTrue(can(MEMBER, action))
        for action in ("manage_members", "audit_read", "admin"):
            self.assertFalse(can(MEMBER, action))

    def test_viewer_read_only(self):
        self.assertEqual(permissions_for("viewer"), {"read"})
        self.assertTrue(can(VIEWER, "read"))
        self.assertFalse(can(VIEWER, "enter"))

    def test_unknown_role_has_nothing(self):
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "read"))

    def test_none_user_denied(self):
        self.assertFalse(can(None, "read"))
        with self.assertRaises(PermissionDenied):
            require(None, "read")

    def test_require_raises_for_forbidden_action(self):
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "decide")
        self.assertTrue(require(ADMIN, "audit_read"))


if __name__ == "__main__":
    unittest.main()
