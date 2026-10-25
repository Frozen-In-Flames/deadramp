"""Access-control tests.

Traces to: UNION-SPEC Core function 10 (Access control); Implementation
contract for ``cyber/access.py``; control families AC-2/AC-3/AC-6 and
IA-2.
"""

import unittest

from cyber_helpers import ADMIN, ANALYST, AUDITOR, VIEWER
from cyber.access import PERMISSIONS, User, can, permissions_for, require
from cyber.errors import CyberError, PermissionDenied, ValidationError

ALL_ACTIONS = {
    "read", "ingest", "triage", "manage_assets", "manage_risks",
    "assess_controls", "audit_read", "admin",
}
ANALYST_PERMISSIONS = {
    "read", "ingest", "triage", "manage_assets", "manage_risks",
    "assess_controls",
}
VIEWER_PERMISSIONS = {"read"}
AUDITOR_PERMISSIONS = {"audit_read"}


def _perm_set(perms):
    """Normalise a permission collection (set/list, or mapping) to a set."""
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v}
    return set(perms)


class TestPermissionsMatrix(unittest.TestCase):
    """Core: Access control — the exact permission matrix in the contract."""

    def test_roles_are_exactly_admin_analyst_viewer_auditor(self):
        """Core: Access control. Contract [L3]: roles are
        admin|analyst|viewer|auditor (the auditor role is the
        High-baseline uplift, AC-5)."""
        self.assertEqual(
            set(PERMISSIONS.keys()),
            {"admin", "analyst", "viewer", "auditor"},
        )

    def test_admin_permissions_are_all_eight_actions(self):
        """Core: Access control. Contract: admin ⊇ all eight actions
        (read, ingest, triage, manage_assets, manage_risks,
        assess_controls, audit_read, admin)."""
        self.assertEqual(_perm_set(PERMISSIONS["admin"]), ALL_ACTIONS)

    def test_analyst_permissions_exact(self):
        """Core: Access control. Contract: analyst = {read, ingest,
        triage, manage_assets, manage_risks, assess_controls}."""
        self.assertEqual(_perm_set(PERMISSIONS["analyst"]), ANALYST_PERMISSIONS)

    def test_viewer_permissions_exact(self):
        """Core: Access control. Contract: viewer = {read}."""
        self.assertEqual(_perm_set(PERMISSIONS["viewer"]), VIEWER_PERMISSIONS)

    def test_auditor_permissions_are_audit_read_only(self):
        """Core: Access control [L3] (AC-5 separation of duties).
        Contract: auditor = {audit_read} -- the role that reviews the
        audit trail holds no operational permission at all."""
        self.assertEqual(
            _perm_set(PERMISSIONS["auditor"]), AUDITOR_PERMISSIONS
        )

    def test_admin_is_strict_superset_of_analyst_and_viewer(self):
        """Core: Access control (AC-6 least privilege ordering)."""
        self.assertTrue(
            _perm_set(PERMISSIONS["analyst"]) < _perm_set(PERMISSIONS["admin"])
        )
        self.assertTrue(
            _perm_set(PERMISSIONS["viewer"]) < _perm_set(PERMISSIONS["analyst"])
        )

    def test_permissions_for_matches_the_matrix(self):
        """Core: Access control. Contract: permissions_for(role) returns
        the role's permission set for each of the four roles [L3]."""
        self.assertEqual(_perm_set(permissions_for("admin")), ALL_ACTIONS)
        self.assertEqual(
            _perm_set(permissions_for("analyst")), ANALYST_PERMISSIONS
        )
        self.assertEqual(_perm_set(permissions_for("viewer")), VIEWER_PERMISSIONS)
        self.assertEqual(
            _perm_set(permissions_for("auditor")), AUDITOR_PERMISSIONS
        )


class TestUserCanAndRequire(unittest.TestCase):
    """Core: Access control — User record, can() and require()."""

    def test_user_stores_name_and_role(self):
        """Core: Access control. Contract: User(name, role)."""
        user = User("dana", "analyst")
        self.assertEqual(user.name, "dana")
        self.assertEqual(user.role, "analyst")

    def test_can_grants_every_permitted_action(self):
        """Core: Access control. can() is true exactly on the matrix."""
        for user, actions in (
            (ADMIN, ALL_ACTIONS),
            (ANALYST, ANALYST_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    self.assertTrue(can(user, action))

    def test_can_denies_every_unpermitted_action(self):
        """Core: Access control (AC-3/AC-6). can() is false off-matrix:
        analyst lacks audit_read/admin; viewer lacks everything except
        read."""
        for user, denied in (
            (ANALYST, {"audit_read", "admin"}),
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
            (ANALYST, ANALYST_PERMISSIONS),
            (VIEWER, VIEWER_PERMISSIONS),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    require(user, action)  # must not raise

    def test_require_denies_viewer_writes(self):
        """Core: Access control (AC-3). Viewer lacks ingest, triage,
        manage_assets, manage_risks and assess_controls."""
        for action in ("ingest", "triage", "manage_assets",
                       "manage_risks", "assess_controls"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(VIEWER, action)

    def test_require_denies_analyst_privileged_actions(self):
        """Core: Access control (AC-6). Analyst lacks audit_read and
        admin."""
        for action in ("audit_read", "admin"):
            with self.subTest(action=action):
                with self.assertRaises(PermissionDenied):
                    require(ANALYST, action)

    def test_require_denies_viewer_and_analyst_audit_read(self):
        """Core: Access control / Audit log (AU-6). audit_read is held
        by admin and the auditor role [L3] only: viewer and analyst
        are both denied."""
        for user in (VIEWER, ANALYST):
            with self.subTest(user=user.role):
                with self.assertRaises(PermissionDenied):
                    require(user, "audit_read")

    def test_auditor_can_only_read_the_audit_trail(self):
        """Core: Access control [L3] (AC-5). The auditor role can()
        audit_read and nothing else: every operational action (read
        included) is off-matrix, so require() denies them all."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        require(AUDITOR, "audit_read")  # must not raise
        for action in ALL_ACTIONS - {"audit_read"}:
            with self.subTest(action=action):
                self.assertFalse(can(AUDITOR, action))
                with self.assertRaises(PermissionDenied):
                    require(AUDITOR, action)

    def test_permission_denied_is_a_cyber_error(self):
        """Core: Access control. Contract: errors live under
        CyberError (cyber/errors.py)."""
        with self.assertRaises(CyberError):
            require(VIEWER, "ingest")

    def test_unknown_role_is_denied_everything(self):
        """Core: Access control. Contract: 'Unknown role or action is
        denied' — an unregistered role holds no permissions."""
        bogus = User("mallory", "superuser")
        with self.assertRaises((PermissionDenied, ValidationError)):
            require(bogus, "read")

    def test_can_with_unknown_role_is_false_or_denied(self):
        """Core: Access control. Contract: unknown role is denied —
        can() never grants an unknown role."""
        try:
            result = can(User("mallory", "superuser"), "read")
        except (PermissionDenied, ValidationError, KeyError):
            return  # a denying raise is also a denial
        self.assertFalse(result)

    def test_unknown_action_is_denied_even_for_admin(self):
        """Core: Access control (AC-6). Contract: unknown action is
        denied to everyone, admin included."""
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")
        self.assertFalse(can(ADMIN, "teleport"))

    def test_permissions_for_unknown_role_is_denied(self):
        """Core: Access control. Contract: unknown role is denied —
        permissions_for() grants it nothing (empty result or a denying
        raise)."""
        try:
            result = permissions_for("superuser")
        except (PermissionDenied, ValidationError, KeyError):
            return
        self.assertEqual(_perm_set(result), set())


if __name__ == "__main__":
    unittest.main()
