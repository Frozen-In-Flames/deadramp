"""RBAC tests.

Traces to: Core function 10 (RBAC, AC-3/AC-6/IA-2 hooks) -- the
admin/manager/viewer permission matrix in ``fleet/access.py``:
baseline read+search for all roles, manager adds write, admin adds
write + audit_read + admin, viewer is read + search only.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, VIEWER
from fleet.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from fleet.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 10 RBAC: exact permission matrix for admin/manager/viewer."""

    def test_admin_has_all_actions(self):
        """Core 10 (AC-3): admin holds every action incl. write, audit_read and admin."""
        self.assertEqual(permissions_for("admin"), set(ACTIONS))
        self.assertTrue({"write", "audit_read", "admin"} <= permissions_for("admin"))

    def test_manager_baseline_plus_write(self):
        """Core 10 (AC-6): manager = read + search + write; NOT audit_read, NOT admin."""
        self.assertEqual(permissions_for("manager"), {"read", "search", "write"})
        self.assertNotIn("audit_read", permissions_for("manager"))

    def test_viewer_read_and_search_only(self):
        """Core 10 (AC-6): viewer = read + search only; no write, no audit_read."""
        self.assertEqual(permissions_for("viewer"), {"read", "search"})
        self.assertNotIn("write", permissions_for("viewer"))
        self.assertNotIn("audit_read", permissions_for("viewer"))

    def test_unknown_role_no_permissions(self):
        """Core 10 (AC-3): unknown role = no permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(VIEWER, "write"))

    def test_can_and_require(self):
        """Core 10: can()/require() agree with the matrix; require raises PermissionDenied."""
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(require(MANAGER, "write"))
        self.assertTrue(require(VIEWER, "search"))
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "write")
        with self.assertRaises(PermissionDenied):
            require(MANAGER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(None, "read")

    def test_matrix_roles_exact(self):
        """Core 10: the matrix covers exactly admin/manager/viewer."""
        self.assertEqual(set(PERMISSIONS), {"admin", "manager", "viewer"})


if __name__ == "__main__":
    unittest.main()
