"""Access-control tests.

Traces to: Core function 11 -- RBAC; contract for
``opsmgmt/access.py``; control families AC-3/AC-5/AC-6, IA-5 (hooks).
"""

import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER
from opsmgmt.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from opsmgmt.errors import OpsError, PermissionDenied

READS = {
    "directory_read", "project_read", "asset_read", "work_read",
    "inspection_read", "usage_read", "workflow_read", "report_read",
}
OPERATOR_SET = READS | {
    "directory_write", "project_write", "asset_write", "work_write",
    "inspection_write", "usage_write",
}
ADMIN_SET = OPERATOR_SET | {"workflow_write", "audit_read"}


class TestMatrix(unittest.TestCase):
    """Core 11: RBAC -- exact permission matrix."""

    def test_roles_exact(self):
        """Core 11: RBAC. Roles are admin/operator/viewer."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "operator", "viewer"})

    def test_actions_exact_16(self):
        """Core 11: RBAC. The contract names exactly 16 actions."""
        self.assertEqual(len(ACTIONS), 16)
        self.assertEqual(set(ACTIONS), ADMIN_SET)

    def test_admin_permissions_exact(self):
        """Core 11: RBAC. Admin has all 16 actions."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)
        self.assertEqual(len(ADMIN_SET), 16)

    def test_operator_permissions_exact(self):
        """Core 11: RBAC. Operator = all reads except audit_read + all writes except workflow_write."""
        self.assertEqual(set(PERMISSIONS["operator"]), OPERATOR_SET)
        self.assertEqual(len(OPERATOR_SET), 14)
        self.assertNotIn("workflow_write", PERMISSIONS["operator"])
        self.assertNotIn("audit_read", PERMISSIONS["operator"])

    def test_viewer_permissions_exact(self):
        """Core 11: RBAC. Viewer = all reads except audit_read, no writes."""
        self.assertEqual(set(PERMISSIONS["viewer"]), READS)
        self.assertEqual(len(READS), 8)
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_permissions_for_matches(self):
        """Core 11: RBAC. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("operator")), OPERATOR_SET)
        self.assertEqual(set(permissions_for("viewer")), READS)

    def test_unknown_role_empty_permissions(self):
        """Core 11: RBAC. Unknown role -> empty permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "work_read"))


class TestCanRequire(unittest.TestCase):
    """Core 11: RBAC -- can()/require()."""

    def test_user_fields(self):
        """Core 11: RBAC. User(name, role) stores both."""
        u = User("dana", "operator")
        self.assertEqual((u.name, u.role), ("dana", "operator"))

    def test_can_matrix(self):
        """Core 11: RBAC. can() is true exactly on the matrix."""
        for user, allowed in ((ADMIN, ADMIN_SET), (OPERATOR, OPERATOR_SET), (VIEWER, READS)):
            for action in allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertTrue(can(user, action))
            for action in ADMIN_SET - allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertFalse(can(user, action))

    def test_require_allows_and_denies(self):
        """Core 11: RBAC (AC-3). require() raises PermissionDenied off-matrix."""
        require(ADMIN, "workflow_write")
        require(ADMIN, "audit_read")
        require(OPERATOR, "work_write")
        require(VIEWER, "work_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "work_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "workflow_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_require_unknown_role_and_action(self):
        """Core 11: RBAC. Unknown role/action denied, even for admin."""
        with self.assertRaises(PermissionDenied):
            require(User("x", "nope"), "work_read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(OpsError):
            require(VIEWER, "work_write")
        with self.assertRaises(PermissionDenied):
            require(None, "work_read")
        self.assertFalse(can(None, "work_read"))


if __name__ == "__main__":
    unittest.main()
