"""Access control (RBAC) tests.

Traces to: Core 10 (Access control / RBAC) and control families
AC-3, AC-6 -- the exact 14-action permission matrix for
admin/operator/viewer.
"""

import unittest

import crm_helpers as H
from crm.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from crm.errors import PermissionDenied

READS = {
    "registry_read", "case_read", "interaction_read", "guide_read",
    "finding_read", "config_read", "report_read",
}
OPERATOR_WRITES = {
    "registry_write", "case_write", "interaction_write",
    "guide_write", "finding_write",
}


class TestMatrix(unittest.TestCase):
    """Core 10: the permission matrix is exactly as contracted."""

    def test_action_count(self):
        """Core 10: 14 actions total."""
        self.assertEqual(len(ACTIONS), 14)
        self.assertEqual(len(set(ACTIONS)), 14)

    def test_admin_has_everything(self):
        """Core 10: admin holds all 14 actions incl. config_write + audit_read."""
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))

    def test_operator_matrix(self):
        """Core 10: operator = all reads except audit_read + operational writes;
        NOT config_write, NOT audit_read."""
        self.assertEqual(PERMISSIONS["operator"], READS | OPERATOR_WRITES)
        self.assertNotIn("config_write", PERMISSIONS["operator"])
        self.assertNotIn("audit_read", PERMISSIONS["operator"])

    def test_viewer_matrix(self):
        """Core 10: viewer = reads only, except audit_read."""
        self.assertEqual(PERMISSIONS["viewer"], READS)
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_permissions_for_unknown_role_empty(self):
        """Core 10 (AC-6): unknown roles hold no permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertEqual(permissions_for(None), set())


class TestCanRequire(unittest.TestCase):
    """Core 10: can()/require() semantics."""

    def test_can(self):
        """Core 10: can() reflects the matrix; None user cannot."""
        self.assertTrue(can(H.ADMIN, "config_write"))
        self.assertFalse(can(H.OPERATOR, "config_write"))
        self.assertFalse(can(H.VIEWER, "case_write"))
        self.assertFalse(can(None, "case_read"))

    def test_require_ok(self):
        """Core 10: require() returns True when permitted."""
        self.assertTrue(require(H.ADMIN, "audit_read"))
        self.assertTrue(require(H.VIEWER, "case_read"))

    def test_require_denied(self):
        """Core 10 (AC-3): require() raises PermissionDenied when not
        permitted, for None users, and for unknown roles/actions."""
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "case_write")
        with self.assertRaises(PermissionDenied):
            require(None, "case_read")
        from crm.access import User
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "case_read")
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "not_an_action")


if __name__ == "__main__":
    unittest.main()
