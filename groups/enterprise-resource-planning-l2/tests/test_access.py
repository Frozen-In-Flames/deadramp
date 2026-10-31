"""Access control: the role/permission matrix (AC-2/AC-3/AC-6;
IA-2 hooks).

The fork's own description claims role-based access authorization
(Infor Federated Security "authorizes users for role-based
access"); this module pins the build's records-level answer: three
roles, a fixed permission matrix, denial for unknown users, roles,
and actions.
"""

import unittest

from erp.access import PERMISSIONS, User, can, permissions_for, require
from erp.errors import PermissionDenied

from erp_helpers import ADMIN, OPERATOR, VIEWER


class AccessTests(unittest.TestCase):
    def test_matrix_shape(self):
        self.assertEqual(permissions_for("admin"),
                         {"read", "register", "record", "approve",
                          "audit_read", "admin"})
        self.assertEqual(permissions_for("operator"),
                         {"read", "register", "record", "approve"})
        self.assertEqual(permissions_for("viewer"), {"read"})
        self.assertEqual(permissions_for("nobody"), set())
        self.assertEqual(set(PERMISSIONS), {"admin", "operator", "viewer"})

    def test_can(self):
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(OPERATOR, "record"))
        self.assertTrue(can(OPERATOR, "approve"))
        self.assertFalse(can(OPERATOR, "audit_read"))
        self.assertTrue(can(VIEWER, "read"))
        self.assertFalse(can(VIEWER, "record"))
        self.assertFalse(can(None, "read"))
        self.assertFalse(can(User("x", "ghost"), "read"))

    def test_require(self):
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(OPERATOR, "register"))
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "record")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")


if __name__ == "__main__":
    unittest.main()
