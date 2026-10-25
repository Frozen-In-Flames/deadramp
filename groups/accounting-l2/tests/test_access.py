"""Access-control tests.

Traces to: UNION-SPEC Core function 12 (Access control) / ranking row
12 (Access control & authentication, 4 siblings); Implementation
contract for ``accounting/access.py``; control families AC-2/AC-3/AC-6
and IA-2.
"""

import unittest

from accounting_helpers import ADMIN, MEMBER, VIEWER
from accounting.access import PERMISSIONS, User, can, permissions_for, require
from accounting.errors import (
    AccountingError,
    PermissionDenied,
    ValidationError,
)

ALL_ACTIONS = {
    "read", "create_book", "enter", "submit", "approve", "pay", "close",
    "manage_members", "audit_read", "admin",
}
MEMBER_PERMISSIONS = {
    "read", "create_book", "enter", "submit", "approve", "pay", "close",
}
VIEWER_PERMISSIONS = {"read"}


def _perm_set(perms):
    """Normalise a permission collection (set/list, or mapping) to a set."""
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v}
    return set(perms)


class TestPermissionsMatrix(unittest.TestCase):
    """Core 12: Access control — the exact permission matrix."""

    def test_roles_are_exactly_admin_member_viewer(self):
        """Core 12: Access control. Contract: roles are
        admin|member|viewer."""
        self.assertEqual(set(PERMISSIONS.keys()), {"admin", "member", "viewer"})

    def test_admin_permissions_are_all_ten_actions(self):
        """Core 12: Access control. Contract: admin holds all ten
        actions (read, create_book, enter, submit, approve, pay, close,
        manage_members, audit_read, admin)."""
        self.assertEqual(_perm_set(PERMISSIONS["admin"]), ALL_ACTIONS)
        self.assertEqual(len(_perm_set(PERMISSIONS["admin"])), 10)

    def test_member_permissions_exact(self):
        """Core 12: Access control. Contract: member = {read,
        create_book, enter, submit, approve, pay, close}."""
        self.assertEqual(_perm_set(PERMISSIONS["member"]), MEMBER_PERMISSIONS)

    def test_viewer_permissions_exact(self):
        """Core 12: Access control. Contract: viewer = {read}."""
        self.assertEqual(_perm_set(PERMISSIONS["viewer"]), VIEWER_PERMISSIONS)

    def test_admin_is_strict_superset_of_member_and_viewer(self):
        """Core 12: Access control (AC-6 least-privilege ordering)."""
        self.assertTrue(
            _perm_set(PERMISSIONS["member"]) < _perm_set(PERMISSIONS["admin"])
        )
        self.assertTrue(
            _perm_set(PERMISSIONS["viewer"]) < _perm_set(PERMISSIONS["member"])
        )

    def test_permissions_for_matches_the_matrix(self):
        """Core 12: Access control. Contract: permissions_for(role)
        returns the role's permission set for each of the three roles."""
        self.assertEqual(_perm_set(permissions_for("admin")), ALL_ACTIONS)
        self.assertEqual(_perm_set(permissions_for("member")), MEMBER_PERMISSIONS)
        self.assertEqual(_perm_set(permissions_for("viewer")), VIEWER_PERMISSIONS)


class TestUserCanAndRequire(unittest.TestCase):
    """Core 12: Access control — User record, can() and require()."""

    def test_user_stores_name_and_role(self):
        """Core 12: Access control. Contract: User(name, role)."""
        user = User("dana", "member")
        self.assertEqual(user.name, "dana")
        self.assertEqual(user.role, "member")

    def test_can_grants_every_permitted_action(self):
        """Core 12: Access control. can() is true exactly on the matrix."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (MEMBER, MEMBER_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    self.assertTrue(can(user, action))

    def test_can_denies_every_unpermitted_action(self):
        """Core 12: Access control (AC-3/AC-6). can() is false
        off-matrix: member lacks manage_members/audit_read/admin;
        viewer lacks everything except read."""
        for user, denied in (
            (MEMBER, {"manage_members", "audit_read", "admin"}),
            (VIEWER, ALL_ACTIONS - {"read"}),
        ):
            for action in denied:
                with self.subTest(user=user.role, action=action):
                    self.assertFalse(can(user, action))

    def test_require_allows_every_permitted_action(self):
        """Core 12: Access control. require() must not raise for
        granted actions."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (MEMBER, MEMBER_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    require(user, action)  # must not raise

    def test_require_denies_viewer_writes(self):
        """Core 12: Access control (AC-3). Viewer lacks create_book,
        enter, submit, approve, pay and close."""
        for action in ("create_book", "enter", "submit", "approve",
                       "pay", "close"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(VIEWER, action)

    def test_require_denies_member_privileged_actions(self):
        """Core 12: Access control (AC-6). Member lacks manage_members,
        audit_read and admin."""
        for action in ("manage_members", "audit_read", "admin"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(MEMBER, action)

    def test_require_denies_viewer_audit_read(self):
        """Core 12: Access control / Core 13 Audit log (AU-6). Viewer
        lacks audit_read."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_permission_denied_is_an_accounting_error(self):
        """Core 12: Access control. Contract: errors live under
        AccountingError."""
        with self.assertRaises(AccountingError):
            require(VIEWER, "enter")

    def test_unknown_role_is_denied_everything(self):
        """Core 12: Access control. An unknown role (an unrecognised
        user) holds no permissions: require() denies it every action."""
        bogus = User("mallory", "superuser")
        for action in ("read", "enter", "admin"):
            with self.subTest(action=action):
                with self.assertRaises((PermissionDenied, ValidationError)):
                    require(bogus, action)

    def test_can_with_unknown_role_is_false_or_denied(self):
        """Core 12: Access control. can() never grants an unknown
        role / unknown user."""
        try:
            result = can(User("mallory", "superuser"), "read")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertFalse(result)

    def test_permissions_for_unknown_role_grants_nothing(self):
        """Core 12: Access control. permissions_for() for an unknown
        role returns no permissions, or denies by raising."""
        try:
            perms = permissions_for("superuser")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertEqual(_perm_set(perms), set())

    def test_unknown_action_is_denied_even_for_admin(self):
        """Core 12: Access control (AC-6). Actions outside the matrix
        are denied to everyone, admin included."""
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        self.assertFalse(can(ADMIN, "teleport"))


if __name__ == "__main__":
    unittest.main()
