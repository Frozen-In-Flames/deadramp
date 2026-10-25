"""Access-control tests.

Traces to: Core function -- Access control (RBAC); contract for
``comm/access.py``; control families AC-2/AC-3/AC-6, IA-2.
"""

import unittest

from comm_helpers import ADMIN, AUDITOR, OPERATOR, VIEWER
from comm.access import PERMISSIONS, User, can, permissions_for, require
from comm.errors import CommError, PermissionDenied

READS = {"contact_read", "channel_read", "template_read", "records_read"}
OPERATOR_SET = READS | {
    "contact_write", "group_write", "template_write",
    "message_compose", "dispatch", "ack_record",
}
ADMIN_SET = OPERATOR_SET | {"channel_write", "audit_read"}
AUDITOR_SET = {"audit_read"}
ALL_ACTIONS = ADMIN_SET


class TestMatrix(unittest.TestCase):
    """Core: Access control -- exact permission matrix."""

    def test_roles_exact(self):
        """Core: Access control (AC-5). Roles are admin/operator/viewer/auditor."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "operator", "viewer", "auditor"})

    def test_admin_permissions_exact(self):
        """Core: Access control. Admin has all 12 actions."""
        self.assertEqual(set(PERMISSIONS["admin"]), ADMIN_SET)

    def test_operator_permissions_exact(self):
        """Core: Access control. Operator = reads + operator writes, no channel_write/audit_read."""
        self.assertEqual(set(PERMISSIONS["operator"]), OPERATOR_SET)

    def test_viewer_permissions_exact(self):
        """Core: Access control. Viewer = reads only."""
        self.assertEqual(set(PERMISSIONS["viewer"]), READS)

    def test_auditor_permissions_exact(self):
        """Core: Access control (AC-5). Auditor = {audit_read} only."""
        self.assertEqual(set(PERMISSIONS["auditor"]), AUDITOR_SET)

    def test_permissions_for_matches(self):
        """Core: Access control. permissions_for(role) returns the matrix set."""
        self.assertEqual(set(permissions_for("admin")), ADMIN_SET)
        self.assertEqual(set(permissions_for("operator")), OPERATOR_SET)
        self.assertEqual(set(permissions_for("viewer")), READS)
        self.assertEqual(set(permissions_for("auditor")), AUDITOR_SET)

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
        for user, allowed in ((ADMIN, ADMIN_SET), (OPERATOR, OPERATOR_SET), (VIEWER, READS), (AUDITOR, AUDITOR_SET)):
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


class TestAuditorRole(unittest.TestCase):
    """Core: Access control (AC-5 separation of duties) -- the auditor
    role holds ONLY audit_read and no operational permission."""

    def test_auditor_permissions_are_exactly_audit_read(self):
        """AC-5: PERMISSIONS["auditor"] == {"audit_read"} exactly, and
        permissions_for("auditor") agrees."""
        self.assertEqual(set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(set(permissions_for("auditor")), {"audit_read"})

    def test_auditor_can_audit_read(self):
        """AC-5: can(AUDITOR, "audit_read") is True and require() allows it."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        require(AUDITOR, "audit_read")  # must not raise

    def test_auditor_can_no_other_action(self):
        """AC-5: can(AUDITOR, each other of the 12 actions) is False."""
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))

    def test_auditor_require_contact_read_raises(self):
        """AC-5: require(AUDITOR, "contact_read") raises PermissionDenied --
        the auditor cannot read contacts."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "contact_read")

    def test_auditor_require_every_other_action_raises(self):
        """AC-5: require() denies the auditor every other action."""
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)


if __name__ == "__main__":
    unittest.main()
