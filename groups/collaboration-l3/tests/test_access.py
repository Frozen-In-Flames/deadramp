"""Access-control tests.

Traces to: UNION-SPEC Core function 10 (Access control) / ranking row 4
(Access control & authentication, 15 siblings); Implementation contract
for ``collab/access.py``; control families AC-2/AC-3/AC-6 and IA-2.
"""

import unittest

from collab_helpers import ADMIN, AUDITOR, MEMBER, VIEWER
from collab.access import PERMISSIONS, User, can, permissions_for, require
from collab.errors import CollabError, PermissionDenied, ValidationError

ALL_ACTIONS = {
    "read", "create_workspace", "post", "share", "schedule",
    "board_edit", "manage_members", "audit_read", "admin",
}
MEMBER_PERMISSIONS = {
    "read", "create_workspace", "post", "share", "schedule", "board_edit",
}
VIEWER_PERMISSIONS = {"read"}


def _perm_set(perms):
    """Normalise a permission collection (set/list, or mapping) to a set."""
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v}
    return set(perms)


class TestPermissionsMatrix(unittest.TestCase):
    """Core: Access control — the exact permission matrix in the contract."""

    def test_roles_are_exactly_admin_member_viewer_auditor(self):
        """Core: Access control. Contract (L3, AC-5): roles are
        admin|member|viewer|auditor."""
        self.assertEqual(
            set(PERMISSIONS.keys()), {"admin", "member", "viewer", "auditor"}
        )

    def test_admin_permissions_are_all_nine_actions(self):
        """Core: Access control. Contract: admin ⊇ all nine actions
        (read, create_workspace, post, share, schedule, board_edit,
        manage_members, audit_read, admin)."""
        self.assertEqual(_perm_set(PERMISSIONS["admin"]), ALL_ACTIONS)

    def test_member_permissions_exact(self):
        """Core: Access control. Contract: member = {read,
        create_workspace, post, share, schedule, board_edit}."""
        self.assertEqual(_perm_set(PERMISSIONS["member"]), MEMBER_PERMISSIONS)

    def test_viewer_permissions_exact(self):
        """Core: Access control. Contract: viewer = {read}."""
        self.assertEqual(_perm_set(PERMISSIONS["viewer"]), VIEWER_PERMISSIONS)

    def test_admin_is_strict_superset_of_member_and_viewer(self):
        """Core: Access control (AC-6 least privilege ordering of roles)."""
        self.assertTrue(_perm_set(PERMISSIONS["member"]) < _perm_set(PERMISSIONS["admin"]))
        self.assertTrue(_perm_set(PERMISSIONS["viewer"]) < _perm_set(PERMISSIONS["member"]))

    def test_permissions_for_matches_the_matrix(self):
        """Core: Access control. Contract: permissions_for(role) returns
        the role's permission set for each of the three roles."""
        self.assertEqual(_perm_set(permissions_for("admin")), ALL_ACTIONS)
        self.assertEqual(_perm_set(permissions_for("member")), MEMBER_PERMISSIONS)
        self.assertEqual(_perm_set(permissions_for("viewer")), VIEWER_PERMISSIONS)


class TestUserCanAndRequire(unittest.TestCase):
    """Core: Access control — User record, can() and require() enforcement."""

    def test_user_stores_name_and_role(self):
        """Core: Access control. Contract: User(name, role)."""
        user = User("dana", "member")
        self.assertEqual(user.name, "dana")
        self.assertEqual(user.role, "member")

    def test_can_grants_every_permitted_action(self):
        """Core: Access control. can() is true exactly on the matrix."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (MEMBER, MEMBER_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    self.assertTrue(can(user, action))

    def test_can_denies_every_unpermitted_action(self):
        """Core: Access control (AC-3/AC-6). can() is false off-matrix:
        member lacks manage_members/audit_read/admin; viewer lacks
        everything except read."""
        for user, denied in (
            (MEMBER, {"manage_members", "audit_read", "admin"}),
            (VIEWER, ALL_ACTIONS - {"read"}),
        ):
            for action in denied:
                with self.subTest(user=user.role, action=action):
                    self.assertFalse(can(user, action))

    def test_require_allows_every_permitted_action(self):
        """Core: Access control. require() must not raise for granted
        actions."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (MEMBER, MEMBER_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    require(user, action)  # must not raise

    def test_require_denies_viewer_writes(self):
        """Core: Access control (AC-3). Viewer lacks post/share/schedule/
        board_edit/create_workspace."""
        for action in ("post", "share", "schedule", "board_edit",
                       "create_workspace"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(VIEWER, action)

    def test_require_denies_member_privileged_actions(self):
        """Core: Access control (AC-6). Member lacks manage_members,
        audit_read and admin."""
        for action in ("manage_members", "audit_read", "admin"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(MEMBER, action)

    def test_require_denies_viewer_audit_read(self):
        """Core: Access control / Audit log (AU-6). Viewer lacks
        audit_read."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_permission_denied_is_a_collab_error(self):
        """Core: Access control. Contract: errors live under CollabError."""
        with self.assertRaises(CollabError):
            require(VIEWER, "post")

    def test_unknown_role_is_denied_everything(self):
        """Core: Access control. An unregistered role holds no
        permissions: require() denies it."""
        bogus = User("mallory", "superuser")
        with self.assertRaises((PermissionDenied, ValidationError)):
            require(bogus, "read")

    def test_can_with_unknown_role_is_false_or_denied(self):
        """Core: Access control. can() never grants an unknown role."""
        try:
            result = can(User("mallory", "superuser"), "read")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertFalse(result)

    def test_unknown_action_is_denied_even_for_admin(self):
        """Core: Access control (AC-6). Actions outside the matrix are
        denied to everyone, admin included."""
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        self.assertFalse(can(ADMIN, "teleport"))


class TestAuditorRole(unittest.TestCase):
    """Core: Access control (AC-5 separation of duties) — the auditor
    role holds ONLY audit_read and no operational permission."""

    def test_auditor_permissions_are_exactly_audit_read(self):
        """AC-5: PERMISSIONS["auditor"] == {"audit_read"} exactly, and
        permissions_for("auditor") agrees."""
        self.assertEqual(_perm_set(PERMISSIONS["auditor"]), {"audit_read"})
        self.assertEqual(_perm_set(permissions_for("auditor")), {"audit_read"})

    def test_auditor_can_audit_read(self):
        """AC-5: can(AUDITOR, "audit_read") is True and require() allows it."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        require(AUDITOR, "audit_read")  # must not raise

    def test_auditor_can_no_other_action(self):
        """AC-5: can(AUDITOR, each other action incl. "read") is False."""
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))

    def test_auditor_require_read_raises_permission_denied(self):
        """AC-5: require(AUDITOR, "read") raises PermissionDenied — the
        auditor cannot read workspaces."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "read")

    def test_auditor_require_every_other_action_raises(self):
        """AC-5: require() denies the auditor every other action."""
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)


if __name__ == "__main__":
    unittest.main()
