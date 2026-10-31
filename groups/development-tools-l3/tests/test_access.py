"""RBAC tests.

Traces to: Core function 9 (RBAC, AC-3/AC-6/IA-2 hooks) -- the
admin/developer/viewer permission matrix in ``devtools/access.py``,
plus the [L3] auditor role (AC-5).
"""

import unittest

from devtools_helpers import ADMIN, AUDITOR, DEVELOPER, VIEWER
from devtools.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from devtools.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 9 RBAC: exact permission matrix for admin/developer/viewer."""

    def test_admin_has_all_actions(self):
        """Core 9 (AC-3): admin holds every action incl. audit_read."""
        self.assertEqual(permissions_for("admin"), set(ACTIONS))
        self.assertEqual(len(ACTIONS), 16)

    def test_developer_all_but_audit_read(self):
        """Core 9 (AC-6): developer holds all reads + all writes + search, NOT audit_read."""
        perms = permissions_for("developer")
        self.assertNotIn("audit_read", perms)
        for action in ACTIONS:
            if action != "audit_read":
                self.assertIn(action, perms)

    def test_viewer_reads_and_search_only(self):
        """Core 9 (AC-6): viewer holds all reads + search only, no writes, no audit_read."""
        perms = permissions_for("viewer")
        self.assertTrue(all(a.endswith("_read") or a == "search" for a in perms))
        self.assertIn("search", perms)
        self.assertNotIn("audit_read", perms)
        self.assertNotIn("project_write", perms)

    def test_unknown_role_no_permissions(self):
        """Core 9 (AC-3): unknown role = no permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(VIEWER, "project_write"))

    def test_can_and_require(self):
        """Core 9: can()/require() agree with the matrix; require raises PermissionDenied."""
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(require(DEVELOPER, "project_write"))
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "project_write")
        with self.assertRaises(PermissionDenied):
            require(DEVELOPER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(None, "project_read")

    def test_matrix_roles_exact(self):
        """Core 9 [L3]: the matrix covers exactly four roles: admin/developer/viewer/auditor."""
        self.assertEqual(set(PERMISSIONS), {"admin", "developer", "viewer", "auditor"})

    def test_auditor_permission_set_exact(self):
        """Core 9 [L3] (AC-5): auditor permission set is exactly {"audit_read"}."""
        self.assertEqual(permissions_for("auditor"), {"audit_read"})
        self.assertTrue(can(AUDITOR, "audit_read"))
        self.assertFalse(can(AUDITOR, "project_read"))
        self.assertFalse(can(AUDITOR, "project_write"))
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "project_read")


if __name__ == "__main__":
    unittest.main()
