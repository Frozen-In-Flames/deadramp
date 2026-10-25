"""Access-control tests.

Traces to: Core function 11 -- RBAC; contract for
``contact/access.py``; control families AC-2/AC-3/AC-6, IA-2.
"""

import unittest

from contact_helpers import ADMIN, OPERATOR, VIEWER
from contact.access import PERMISSIONS, User, can, permissions_for, require
from contact.errors import ContactError, PermissionDenied

READS = {
    "directory_read", "queue_read", "case_read", "callback_read",
    "interaction_read", "alert_read", "rule_read", "report_read",
}
OPERATOR_SET = READS | {
    "directory_write", "queue_write", "case_write", "callback_write",
    "interaction_write", "alert_write",
}
ADMIN_SET = OPERATOR_SET | {"rule_write", "audit_read"}


class TestMatrix(unittest.TestCase):
    """Core 11: RBAC -- exact permission matrix."""

    def test_roles_exact(self):
        """Core 11: RBAC. Roles are admin/operator/viewer."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "operator", "viewer"})

    def test_admin_permissions_exact(self):
        """Core 11: RBAC. Admin has all 16 actions."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)
        self.assertEqual(len(ADMIN_SET), 16)

    def test_operator_permissions_exact(self):
        """Core 11: RBAC. Operator = viewer reads + six writes, no rule_write/audit_read."""
        self.assertEqual(set(PERMISSIONS["operator"]), OPERATOR_SET)

    def test_viewer_permissions_exact(self):
        """Core 11: RBAC. Viewer = all reads except audit_read."""
        self.assertEqual(set(PERMISSIONS["viewer"]), READS)
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_permissions_for_matches(self):
        """Core 11: RBAC. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("operator")), OPERATOR_SET)
        self.assertEqual(set(permissions_for("viewer")), READS)

    def test_unknown_role_empty_permissions(self):
        """Core 11: RBAC. Unknown role -> empty permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "case_read"))


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
        require(ADMIN, "rule_write")
        require(ADMIN, "audit_read")
        require(OPERATOR, "case_write")
        require(VIEWER, "case_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "case_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "rule_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_require_unknown_role_and_action(self):
        """Core 11: RBAC. Unknown role/action denied, even for admin."""
        with self.assertRaises(PermissionDenied):
            require(User("x", "nope"), "case_read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(ContactError):
            require(VIEWER, "case_write")
        with self.assertRaises(PermissionDenied):
            require(None, "case_read")
        self.assertFalse(can(None, "case_read"))


if __name__ == "__main__":
    unittest.main()
