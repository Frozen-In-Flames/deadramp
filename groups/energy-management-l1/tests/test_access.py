"""Access control: the role matrix (AU/AC families, Low/L1 baseline)."""

import unittest

from energy.access import PERMISSIONS, User, can, require
from energy.errors import PermissionDenied

from energy_helpers import ADMIN, MEMBER, VIEWER


class AccessTests(unittest.TestCase):
    def test_matrix_shape(self):
        self.assertEqual(
            PERMISSIONS["admin"],
            {"read", "register", "conduct", "observe", "alert",
             "advise", "audit_read", "admin"})
        self.assertEqual(
            PERMISSIONS["member"],
            {"read", "register", "conduct", "observe", "alert", "advise"})
        self.assertEqual(PERMISSIONS["viewer"], {"read"})

    def test_can(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(MEMBER, "conduct"))
        self.assertFalse(can(MEMBER, "audit_read"))
        self.assertFalse(can(VIEWER, "register"))
        self.assertFalse(can(None, "read"))
        self.assertFalse(can(User("x", "nobody"), "read"))

    def test_require_passes(self):
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(VIEWER, "read"))

    def test_require_denies(self):
        for user, action in [(VIEWER, "register"), (MEMBER, "audit_read"),
                             (None, "read"), (User("x", "ghost"), "read")]:
            with self.assertRaises(PermissionDenied):
                require(user, action)


if __name__ == "__main__":
    unittest.main()
