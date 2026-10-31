"""Access control: the role matrix (AC family, Moderate/L2 baseline)."""

import unittest

from storage.access import PERMISSIONS, User, can, require
from storage.errors import PermissionDenied

from storage_helpers import ADMIN, OPERATOR, VIEWER


class AccessTests(unittest.TestCase):
    def test_matrix_shape(self):
        self.assertEqual(
            PERMISSIONS["admin"],
            {"read", "register", "archive", "discover", "supervise",
             "enforce", "retrieve", "custody", "audit_read", "admin"})
        self.assertEqual(
            PERMISSIONS["operator"],
            {"read", "register", "archive", "discover", "supervise",
             "enforce", "retrieve", "custody"})
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_can(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(OPERATOR, "archive"))
        self.assertFalse(can(OPERATOR, "audit_read"))
        self.assertFalse(can(VIEWER, "register"))
        self.assertFalse(can(None, "read"))
        self.assertFalse(can(User("x", "nobody"), "read"))

    def test_require_passes(self):
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(VIEWER, "read"))

    def test_require_denies(self):
        for user, action in [(VIEWER, "register"), (OPERATOR, "audit_read"),
                             (None, "read"), (User("x", "ghost"), "read")]:
            with self.assertRaises(PermissionDenied):
                require(user, action)


if __name__ == "__main__":
    unittest.main()
