"""Access-control tests.

Traces to: UNION-SPEC Core function 9 (Access control) / ranking rows 10
(Access control & authentication, 19 siblings) and 11 (Audit logging);
Implementation contract for ``analytics/access.py``; control families
AC-2/AC-3/AC-6 and IA-2.
"""

import unittest

from analytics_helpers import ADMIN, ANALYST, AUDITOR, VIEWER
from analytics.access import PERMISSIONS, ROLES, User, can, require
from analytics.errors import AnalyticsError, PermissionDenied, ValidationError


def _perm_set(role):
    """Normalise a PERMISSIONS entry (set/list, or mapping) to a set."""
    perms = PERMISSIONS[role]
    if isinstance(perms, dict):
        return {k for k, v in perms.items() if v}
    return set(perms)


class TestPermissionsMatrix(unittest.TestCase):
    """Core: Access control — the exact permission matrix in the contract."""

    def test_roles_are_exactly_admin_analyst_viewer_auditor(self):
        """Core: Access control. L2 contract roles admin|analyst|viewer,
        plus the L3 High uplift role auditor (AC-5)."""
        self.assertEqual(
            set(PERMISSIONS.keys()), {"admin", "analyst", "viewer", "auditor"}
        )

    def test_admin_permissions(self):
        """Core: Access control. Contract: admin superset of
        {ingest, query, export, audit_read, admin}."""
        self.assertTrue(
            {"ingest", "query", "export", "audit_read", "admin"}
            <= _perm_set("admin")
        )

    def test_analyst_permissions_exact(self):
        """Core: Access control. Contract: analyst = {ingest, query, export}."""
        self.assertEqual(_perm_set("analyst"), {"ingest", "query", "export"})

    def test_viewer_permissions_exact(self):
        """Core: Access control. Contract: viewer = {query, export}."""
        self.assertEqual(_perm_set("viewer"), {"query", "export"})

    def test_admin_is_strict_superset_of_analyst_and_viewer(self):
        """Core: Access control (AC-6 least privilege ordering of roles)."""
        self.assertTrue(_perm_set("analyst") < _perm_set("admin"))
        self.assertTrue(_perm_set("viewer") < _perm_set("analyst"))


class TestUserAndRequire(unittest.TestCase):
    """Core: Access control — User record and require() enforcement."""

    def test_user_stores_name_and_role(self):
        """Core: Access control. Contract: User(name, role)."""
        user = User("dana", "analyst")
        self.assertEqual(user.name, "dana")
        self.assertEqual(user.role, "analyst")

    def test_require_allows_every_permitted_action(self):
        """Core: Access control. require() must not raise for granted actions."""
        for user, actions in (
            (ADMIN, ("ingest", "query", "export", "audit_read", "admin")),
            (ANALYST, ("ingest", "query", "export")),
            (VIEWER, ("query", "export")),
        ):
            for action in actions:
                with self.subTest(user=user.role, action=action):
                    require(user, action)  # must not raise

    def test_require_denies_viewer_ingest(self):
        """Core: Access control (AC-3). Viewer lacks ingest."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "ingest")

    def test_require_denies_viewer_audit_read(self):
        """Core: Access control / Audit log. Viewer lacks audit_read."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "audit_read")

    def test_require_denies_analyst_audit_read_and_admin(self):
        """Core: Access control (AC-6). Analyst lacks audit_read and admin."""
        with self.assertRaises(PermissionDenied):
            require(ANALYST, "audit_read")
        with self.assertRaises(PermissionDenied):
            require(ANALYST, "admin")

    def test_require_denies_viewer_admin(self):
        """Core: Access control. Viewer lacks admin."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "admin")

    def test_permission_denied_is_an_analytics_error(self):
        """Core: Access control. Contract: errors live under AnalyticsError."""
        with self.assertRaises(AnalyticsError):
            require(VIEWER, "ingest")

    def test_unknown_role_is_denied_everything(self):
        """Core: Access control. An unregistered role holds no permissions."""
        with self.assertRaises((PermissionDenied, ValidationError)):
            bogus = User("mallory", "superuser")
            require(bogus, "query")

    def test_unknown_action_is_denied_even_for_admin(self):
        """Core: Access control (AC-6). Actions outside the matrix are denied."""
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport")


class TestAuditorRole(unittest.TestCase):
    """L3 High uplift: Access control (AC-5 separation of duties).

    The auditor role exists to review the audit trail and nothing else:
    it holds audit_read ONLY and is denied every operational action.
    """

    def test_auditor_in_roles_tuple(self):
        """AC-5: ROLES includes auditor alongside the L2 roles."""
        self.assertIn("auditor", ROLES)
        self.assertEqual(
            set(ROLES), {"admin", "analyst", "viewer", "auditor"}
        )

    def test_auditor_permissions_exact(self):
        """AC-5: auditor = {"audit_read"} exactly, nothing more."""
        self.assertEqual(_perm_set("auditor"), {"audit_read"})

    def test_auditor_may_audit_read(self):
        """AC-5 / AU-6: the auditor can review the audit trail."""
        require(AUDITOR, "audit_read")  # must not raise
        self.assertTrue(can(AUDITOR, "audit_read"))

    def test_auditor_denied_ingest(self):
        """AC-5: auditor cannot ingest."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "ingest")

    def test_auditor_denied_query(self):
        """AC-5: auditor cannot query datasets."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "query")

    def test_auditor_denied_export(self):
        """AC-5: auditor cannot export."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "export")

    def test_auditor_denied_admin(self):
        """AC-5: auditor holds no admin permission."""
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "admin")

    def test_auditor_permissions_disjoint_from_operations(self):
        """AC-5: audit review and operations are fully separated --
        no operational permission leaks into the auditor role."""
        self.assertFalse(
            _perm_set("auditor") & {"ingest", "query", "export", "admin"}
        )


if __name__ == "__main__":
    unittest.main()
