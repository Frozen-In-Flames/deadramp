"""Access-control tests.

Traces to: UNION-SPEC Core function 9 (Access control & API keys) and
the Implementation contract for ``aigateway/access.py``: roles
admin|member|viewer, actions read, registry_write, invoke, eval_run,
usage_read, policy_write, audit_read, admin; control families AC-2,
AC-3, AC-6, IA-2.
"""

import unittest

from aigateway_helpers import ADMIN, MEMBER, VIEWER
from aigateway.access import PERMISSIONS, User, can, permissions_for, require
from aigateway.errors import PermissionDenied

ALL_ACTIONS = {
    "read", "registry_write", "invoke", "eval_run",
    "usage_read", "policy_write", "audit_read", "admin",
}


class TestPermissionMatrix(unittest.TestCase):
    """Core function 9: Access control — the pinned permission matrix."""

    def test_admin_has_all_eight_actions(self):
        """Core 9 / access contract: admin ⊇ all eight actions."""
        self.assertEqual(PERMISSIONS["admin"], ALL_ACTIONS)
        self.assertEqual(permissions_for("admin"), ALL_ACTIONS)

    def test_member_matrix_exact(self):
        """Core 9 / access contract: member = {read, registry_write,
        invoke, eval_run, usage_read} — no policy_write, audit_read,
        or admin."""
        expected = {"read", "registry_write", "invoke", "eval_run", "usage_read"}
        self.assertEqual(PERMISSIONS["member"], expected)
        self.assertEqual(permissions_for("member"), expected)

    def test_viewer_matrix_exact(self):
        """Core 9 / access contract: viewer = {read, usage_read} only."""
        self.assertEqual(PERMISSIONS["viewer"], {"read", "usage_read"})
        self.assertEqual(permissions_for("viewer"), {"read", "usage_read"})

    def test_unknown_role_has_no_permissions(self):
        """Core 9 / access contract: permissions_for(unknown) is empty."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertEqual(permissions_for(""), set())

    def test_can_reflects_matrix(self):
        """Core 9: can(user, action) follows the matrix per role."""
        self.assertTrue(can(ADMIN, "policy_write"))
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(MEMBER, "invoke"))
        self.assertFalse(can(MEMBER, "policy_write"))
        self.assertFalse(can(MEMBER, "audit_read"))
        self.assertFalse(can(MEMBER, "admin"))
        self.assertTrue(can(VIEWER, "read"))
        self.assertTrue(can(VIEWER, "usage_read"))
        self.assertFalse(can(VIEWER, "invoke"))
        self.assertFalse(can(VIEWER, "registry_write"))

    def test_can_none_user_is_false(self):
        """Core 9: can(None, action) is False for every action."""
        for action in ALL_ACTIONS:
            self.assertFalse(can(None, action))

    def test_can_unknown_action_is_false(self):
        """Core 9: an action outside the pinned eight is never allowed."""
        self.assertFalse(can(ADMIN, "destroy_everything"))

    def test_require_passes_for_allowed(self):
        """Core 9: require() returns True for a permitted action."""
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(MEMBER, "registry_write"))
        self.assertTrue(require(VIEWER, "usage_read"))

    def test_require_raises_for_denied(self):
        """Core 9: require() raises PermissionDenied for a forbidden
        action (AC-3 access enforcement)."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "invoke")
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "admin")

    def test_require_raises_for_none_and_unknown_role(self):
        """Core 9: require() denies a missing user and an unknown role."""
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "read")

    def test_user_dataclass_fields(self):
        """Core 9 / access contract: User(name, role) carries both."""
        user = User("bob", "member")
        self.assertEqual((user.name, user.role), ("bob", "member"))


if __name__ == "__main__":
    unittest.main()
