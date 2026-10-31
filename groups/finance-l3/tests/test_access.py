"""Access-control tests.

Traces to: UNION-SPEC Core function 10 (Access control) and Core
function 9 (API access); Implementation contract for
``finance/access.py``; control families AC-2/AC-3/AC-6 and IA-2.
"""

import unittest

from finance_helpers import ADMIN, AUDITOR, MEMBER, VIEWER
from finance.access import PERMISSIONS, User, can, permissions_for, require
from finance.errors import FinanceError, PermissionDenied, ValidationError

ALL_ACTIONS = {
    "read", "create_program", "enter", "decide", "record",
    "manage_members", "audit_read", "admin",
}
MEMBER_PERMISSIONS = {"read", "create_program", "enter", "decide", "record"}
VIEWER_PERMISSIONS = {"read"}


def _perm_set(perms):
    """Normalise a permission collection (set/list, or mapping) to a set."""
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v}
    return set(perms)


class TestPermissionsMatrix(unittest.TestCase):
    """Core 10: Access control — the exact permission matrix."""

    def test_roles_are_exactly_admin_member_viewer_auditor(self):
        """Core 10: Access control [L3]. Contract: roles are
        admin|member|viewer|auditor."""
        self.assertEqual(
            set(PERMISSIONS.keys()),
            {"admin", "member", "viewer", "auditor"},
        )

    def test_admin_permissions_are_all_eight_actions(self):
        """Core 10: Access control. Contract: admin holds all eight
        actions (read, create_program, enter, decide, record,
        manage_members, audit_read, admin)."""
        self.assertEqual(_perm_set(PERMISSIONS["admin"]), ALL_ACTIONS)
        self.assertEqual(len(_perm_set(PERMISSIONS["admin"])), 8)

    def test_member_permissions_exact(self):
        """Core 10: Access control. Contract: member = {read,
        create_program, enter, decide, record}."""
        self.assertEqual(_perm_set(PERMISSIONS["member"]), MEMBER_PERMISSIONS)

    def test_viewer_permissions_exact(self):
        """Core 10: Access control. Contract: viewer = {read}."""
        self.assertEqual(_perm_set(PERMISSIONS["viewer"]), VIEWER_PERMISSIONS)

    def test_admin_is_strict_superset_of_member_and_viewer(self):
        """Core 10: Access control (AC-6 least-privilege ordering)."""
        self.assertTrue(
            _perm_set(PERMISSIONS["member"]) < _perm_set(PERMISSIONS["admin"])
        )
        self.assertTrue(
            _perm_set(PERMISSIONS["viewer"]) < _perm_set(PERMISSIONS["member"])
        )

    def test_permissions_for_matches_the_matrix(self):
        """Core 10: Access control. Contract: permissions_for(role)
        returns the role's permission set for each of the three roles."""
        self.assertEqual(_perm_set(permissions_for("admin")), ALL_ACTIONS)
        self.assertEqual(_perm_set(permissions_for("member")), MEMBER_PERMISSIONS)
        self.assertEqual(_perm_set(permissions_for("viewer")), VIEWER_PERMISSIONS)


class TestUserCanAndRequire(unittest.TestCase):
    """Core 10: Access control — User record, can() and require()."""

    def test_user_stores_name_and_role(self):
        """Core 10: Access control. Contract: User(name, role)."""
        user = User("dana", "member")
        self.assertEqual(user.name, "dana")
        self.assertEqual(user.role, "member")

    def test_can_grants_every_permitted_action(self):
        """Core 10: Access control. can() is true exactly on the matrix."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (MEMBER, MEMBER_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    self.assertTrue(can(user, action))

    def test_can_denies_every_unpermitted_action(self):
        """Core 10: Access control (AC-3/AC-6). can() is false
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
        """Core 10: Access control. require() must not raise for
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
        """Core 10: Access control (AC-3). Viewer lacks create_program,
        enter, decide and record."""
        for action in ("create_program", "enter", "decide", "record"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(VIEWER, action)

    def test_require_denies_member_privileged_actions(self):
        """Core 10: Access control (AC-6). Member lacks manage_members,
        audit_read and admin."""
        for action in ("manage_members", "audit_read", "admin"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(MEMBER, action)

    def test_require_denies_viewer_audit_read(self):
        """Core 10: Access control / Core 11 Audit log (AU-6). Viewer
        lacks audit_read."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_permission_denied_is_a_finance_error(self):
        """Core 10: Access control. Contract: errors live under
        FinanceError (finance/errors.py)."""
        with self.assertRaises(FinanceError):
            require(VIEWER, "enter")

    def test_unknown_role_is_denied_everything(self):
        """Core 10: Access control. An unknown role (an unrecognised
        user) holds no permissions: require() denies it every action."""
        bogus = User("mallory", "superuser")
        for action in ("read", "enter", "admin"):
            with self.subTest(action=action):
                with self.assertRaises((PermissionDenied, ValidationError)):
                    require(bogus, action)

    def test_can_with_unknown_role_is_false_or_denied(self):
        """Core 10: Access control. can() never grants an unknown
        role / unknown user."""
        try:
            result = can(User("mallory", "superuser"), "read")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertFalse(result)

    def test_permissions_for_unknown_role_grants_nothing(self):
        """Core 10: Access control. permissions_for() for an unknown
        role returns no permissions, or denies by raising."""
        try:
            perms = permissions_for("superuser")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertEqual(_perm_set(perms), set())

    def test_unknown_action_is_denied_even_for_admin(self):
        """Core 10: Access control (AC-6). Actions outside the matrix
        are denied to everyone, admin included."""
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        self.assertFalse(can(ADMIN, "teleport"))


class TestAuditorRole(unittest.TestCase):
    """Core 10 [L3] (AC-5): the auditor role holds audit_read ONLY —
    separation of duties: audit review exists as a duty separable
    from administration and from every operational permission."""

    def test_auditor_permissions_are_exactly_audit_read(self):
        """AC-5: auditor's permission set is exactly {"audit_read"}."""
        self.assertEqual(_perm_set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(_perm_set(permissions_for("auditor")), {"audit_read"})

    def test_auditor_can_read_audit(self):
        """AC-5: can(AUDITOR, "audit_read") is true and require()
        does not raise for it."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        require(AUDITOR, "audit_read")  # must not raise

    def test_auditor_cannot_read(self):
        """AC-5: the auditor holds no operational read — require()
        raises PermissionDenied for auditor on read."""
        self.assertFalse(can(AUDITOR, "read"))
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "read")

    def test_auditor_cannot_write_or_act(self):
        """AC-5: the auditor holds no operational permission at all —
        require() raises PermissionDenied for auditor on enter,
        decide, record and create_program (and likewise on
        manage_members and admin)."""
        for action in (
            "enter", "decide", "record", "create_program",
            "manage_members", "admin",
        ):
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)

    def test_existing_roles_unchanged_by_auditor(self):
        """AC-5: adding the auditor moved no existing permission —
        admin still holds all eight actions, and the member and
        viewer permission sets are unchanged."""
        self.assertEqual(_perm_set(PERMISSIONS["admin"]), ALL_ACTIONS)
        self.assertEqual(_perm_set(PERMISSIONS["member"]), MEMBER_PERMISSIONS)
        self.assertEqual(_perm_set(PERMISSIONS["viewer"]), VIEWER_PERMISSIONS)


if __name__ == "__main__":
    unittest.main()
