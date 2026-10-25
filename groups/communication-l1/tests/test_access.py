"""Access-control tests.

Traces to: Core function -- Access control (RBAC); contract for
``comm/access.py``; control families AC-2/AC-3/AC-6, IA-2.
"""

import unittest

from comm_helpers import ADMIN, OPERATOR, VIEWER
from comm.access import PERMISSIONS, User, can, permissions_for, require
from comm.errors import CommError, PermissionDenied

READS = {"contact_read", "channel_read", "template_read", "records_read"}
OPERATOR_SET = READS | {
    "contact_write", "group_write", "template_write",
    "message_compose", "dispatch", "ack_record",
}
ADMIN_SET = OPERATOR_SET | {"channel_write", "audit_read"}


class TestMatrix(unittest.TestCase):
    """Core: Access control -- exact permission matrix."""

    def test_roles_exact(self):
        """Core: Access control. Roles are admin/operator/viewer."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "operator", "viewer"})

    def test_admin_permissions_exact(self):
        """Core: Access control. Admin has all 12 actions."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)

    def test_operator_permissions_exact(self):
        """Core: Access control. Operator = reads + operator writes, no channel_write/audit_read."""
        self.assertEqual(set(PERMISSIONS["operator"]), OPERATOR_SET)

    def test_viewer_permissions_exact(self):
        """Core: Access control. Viewer = reads only."""
        self.assertEqual(set(PERMISSIONS["viewer"]), READS)

    def test_permissions_for_matches(self):
        """Core: Access control. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("operator")), OPERATOR_SET)
        self.assertEqual(set(permissions_for("viewer")), READS)

    def test_unknown_role_empty_permissions(self):
        """Core: Access control. Unknown role -> empty permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(User("mallory", "superuser"), "contact_read"))


class TestCanRequire(unittest.TestCase):
    """Core: Access control -- can()/require()."""

    def test_user_fields(self):
        """Core: Access control. User(name, role) stores both."""
        u = User("dana", "operator")
        self.assertEqual((u.name, u.role), ("dana", "operator"))

    def test_can_matrix(self):
        """Core: Access control. can() is true exactly on the matrix."""
        for user, allowed in ((ADMIN, ADMIN_SET), (OPERATOR, OPERATOR_SET), (VIEWER, READS)):
            for action in allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertTrue(can(user, action))
            for action in ADMIN_SET - allowed:
                with self.subTest(role=user.role, action=action):
                    self.assertFalse(can(user, action))

    def test_require_allows_and_denies(self):
        """Core: Access control (AC-3). require() raises PermissionDenied off-matrix."""
        require(ADMIN, "channel_write")
        require(OPERATOR, "dispatch")
        require(VIEWER, "contact_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "dispatch")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "channel_write")
        with self.assertRaises(PermissionDenied):
            require(OPERATOR, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "contact_write")

    def test_require_unknown_role_and_action(self):
        """Core: Access control. Unknown role/action denied, even for admin."""
        with self.assertRaises(PermissionDenied):
            require(User("x", "nope"), "contact_read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        with self.assertRaises(CommError):
            require(VIEWER, "dispatch")
        with self.assertRaises(PermissionDenied):
            require(None, "contact_read")
        self.assertFalse(can(None, "contact_read"))


if __name__ == "__main__":
    unittest.main()
