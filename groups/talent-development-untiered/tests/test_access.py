import unittest

from talentdev.access import PERMISSIONS, ROLES, User, can, permissions_for, require
from talentdev.errors import PermissionDenied
from talentdev_helpers import ADMIN, OPERATOR, VIEWER


class TestAccess(unittest.TestCase):
    def test_roles_and_matrix(self):
        self.assertEqual(ROLES, ("admin", "operator", "viewer"))
        self.assertEqual(
            PERMISSIONS["admin"],
            {"read", "register", "programs", "assess", "insights",
             "decide", "audit_read", "admin"})
        self.assertEqual(
            PERMISSIONS["operator"],
            {"read", "register", "programs", "assess", "insights",
             "decide"})
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_can_and_permissions_for(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(OPERATOR, "programs"))
        self.assertFalse(can(OPERATOR, "audit_read"))
        self.assertFalse(can(VIEWER, "programs"))
        self.assertTrue(can(VIEWER, "read"))
        self.assertFalse(can(None, "read"))
        self.assertEqual(permissions_for("nonsense"), set())

    def test_require(self):
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(OPERATOR, "decide"))
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "programs")
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")


if __name__ == "__main__":
    unittest.main()
