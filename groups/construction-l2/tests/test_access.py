"""Access-control tests.

Traces to: Core function -- RBAC; contract for
``construct/access.py`` (17 actions); control families AC-2/AC-3/AC-6, IA-2.
"""

import unittest

from construct_helpers import ADMIN, OPERATOR, VIEWER
from construct.access import ACTIONS, PERMISSIONS, User, can, permissions_for, require
from construct.errors import ConstructError, PermissionDenied

READS = {
    "project_read", "org_read", "document_read", "contract_read",
    "record_read", "workforce_read", "cost_read", "report_read",
}
ALL_READS = READS | {"audit_read"}
WRITES = {
    "project_write", "org_write", "document_write", "contract_write",
    "record_write", "workforce_write", "cost_write", "violation_write",
}
VIEWER_SET = READS
OPERATOR_SET = READS | (WRITES - {"violation_write"})
ADMIN_SET = ALL_READS | WRITES


class TestMatrix(unittest.TestCase):
    """RBAC: exact permission matrix (17 actions)."""

    def test_roles_exact(self):
        """RBAC. Roles are admin/operator/viewer."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "operator", "viewer"})

    def test_actions_exact_17(self):
        """RBAC. ACTIONS is exactly the 17 contract actions."""
        self.assertEqual(set(ACTIONS), ADMIN_SET)
        self.assertEqual(len(ACTIONS), 17)

    def test_admin_permissions_exact(self):
        """RBAC. Admin has all 17 actions."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)
        self.assertEqual(len(ADMIN_SET), 17)

    def test_operator_permissions_exact(self):
        """RBAC. Operator = reads except audit_read + writes except violation_write."""
        self.assertEqual(set(PERMISSIONS["operator"]), OPERATOR_SET)
        self.assertNotIn("violation_write", PERMISSIONS["operator"])
        self.assertNotIn("audit_read", PERMISSIONS["operator"])

    def test_viewer_permissions_exact(self):
        """RBAC. Viewer = all reads except audit_read, no writes."""
        self.assertEqual(set(PERMISSIONS["viewer"]), VIEWER_SET)
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_permissions_for_matches(self):
        """RBAC. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("operator")), OPERATOR_SET)
        self.assertEqual(set(permissions_for("viewer")), VIEWER_SET)

    def test_unknown_role_empty_permissions(self):
        """RBAC. Unknown role -> empty permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "project_read"))


class TestCanRequire(unittest.TestCase):
    """RBAC: can()/require()."""

    def test_user_fields(self):
        """RBAC. User(name, role) stores both."""
        u = User("dana", "operator")
        self.assertEqual((u.name, u.role), ("dana", "operator"))

    def test_can_matrix(self):
        """RBAC. can() is true exactly on the matrix."""
        for user, allowed in ((ADMIN, ADMIN_SET), (OPERATOR, OPERATOR_SET), (VIEWER, VIEWER_SET)):
            for action in allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertTrue(can(user, action))
            for action in ADMIN_SET - allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertFalse(can(user, action))

    def test_require_allows_and_denies(self):
        """RBAC (AC-3). require() raises PermissionDenied off-matrix."""
        require(ADMIN, "violation_write")
        require(ADMIN, "audit_read")
        require(OPERATOR, "record_write")
        require(VIEWER, "project_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "project_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "violation_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_require_unknown_role_and_action(self):
        """RBAC. Unknown role/action denied, even for admin."""
        with self.assertRaises(PermissionDenied):
            require(User("x", "nope"), "project_read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(ConstructError):
            require(VIEWER, "project_write")
        with self.assertRaises(PermissionDenied):
            require(None, "project_read")
        self.assertFalse(can(None, "project_read"))


if __name__ == "__main__":
    unittest.main()
