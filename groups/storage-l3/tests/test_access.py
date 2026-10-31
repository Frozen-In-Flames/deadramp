"""Access control: the role matrix (AC family, High/L3-adjacent
baseline), including the separated auditor role [L3] (AC-5)."""

import unittest

from storage.access import PERMISSIONS, ROLES, User, can, require
from storage.errors import PermissionDenied

from storage_helpers import ADMIN, AUDITOR, OPERATOR, VIEWER


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
        # [L3] AC-5: the auditor holds audit_read and nothing else.
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})
        self.assertEqual(ROLES, ("admin", "operator", "viewer", "auditor"))

    def test_can(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(OPERATOR, "archive"))
        self.assertFalse(can(OPERATOR, "audit_read"))
        self.assertFalse(can(VIEWER, "register"))
        self.assertFalse(can(None, "read"))
        self.assertFalse(can(User("x", "nobody"), "read"))

    def test_auditor_separation(self):
        """AC-5 [L3]: the auditor can review the audit trail and
        nothing else -- no operational read, no write of any kind."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        for action in ("read", "register", "archive", "discover",
                       "supervise", "enforce", "retrieve", "custody",
                       "admin"):
            self.assertFalse(can(AUDITOR, action), action)

    def test_require_passes(self):
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(VIEWER, "read"))
        self.assertTrue(require(AUDITOR, "audit_read"))

    def test_require_denies(self):
        for user, action in [(VIEWER, "register"), (OPERATOR, "audit_read"),
                             (AUDITOR, "read"), (AUDITOR, "register"),
                             (None, "read"), (User("x", "ghost"), "read")]:
            with self.assertRaises(PermissionDenied):
                require(user, action)


if __name__ == "__main__":
    unittest.main()
