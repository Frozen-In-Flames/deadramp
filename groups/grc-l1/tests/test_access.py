"""Access-control tests.

Traces to: Core function 9 (RBAC — role permission matrix enforced on
every operation, admin/member/viewer granularity); control family
AC-3 / AC-6 (access enforcement, least privilege) and IA-2 (identity
is supplied by the embedding organization; these are hooks, not an
IdP).
"""

import unittest

from grc_helpers import ADMIN, MEMBER, VIEWER
from grc.access import PERMISSIONS, ROLES, can, permissions_for, require
from grc.errors import PermissionDenied

ADMIN_ACTIONS = {
    "read",
    "manage_frameworks",
    "manage_systems",
    "manage_indicators",
    "record_results",
    "manage_evidence",
    "review_evidence",
    "manage_findings",
    "manage_assessments",
    "manage_authorizations",
    "audit_read",
    "admin",
}

MEMBER_ACTIONS = {
    "read",
    "manage_systems",
    "manage_indicators",
    "record_results",
    "manage_evidence",
    "manage_findings",
    "manage_assessments",
}


class TestPermissionMatrix(unittest.TestCase):
    """Core 9 RBAC: the exact permission matrix."""

    def test_roles_are_admin_member_viewer(self):
        """Core 9 RBAC. The role set is exactly admin/member/viewer."""
        self.assertEqual(set(ROLES), {"admin", "member", "viewer"})
        self.assertEqual(set(PERMISSIONS), {"admin", "member", "viewer"})

    def test_admin_matrix_is_exact(self):
        """Core 9 RBAC. Admin holds all 12 actions."""
        self.assertEqual(PERMISSIONS["admin"], ADMIN_ACTIONS)
        self.assertEqual(permissions_for("admin"), ADMIN_ACTIONS)

    def test_member_matrix_is_exact(self):
        """Core 9 RBAC. Member holds exactly 7 actions: no framework
        registration, no evidence review, no authorization management,
        no audit read, no admin."""
        self.assertEqual(PERMISSIONS["member"], MEMBER_ACTIONS)
        self.assertEqual(permissions_for("member"), MEMBER_ACTIONS)

    def test_viewer_matrix_is_read_only(self):
        """Core 9 RBAC (AC-6 least privilege). Viewer holds read only."""
        self.assertEqual(PERMISSIONS["viewer"], {"read"})
        self.assertEqual(permissions_for("viewer"), {"read"})


class TestCanAndRequire(unittest.TestCase):
    """Core 9 RBAC: can() / require() behaviour."""

    def test_can_reflects_the_matrix(self):
        """Core 9 RBAC. can() agrees with the matrix for each role."""
        self.assertTrue(can(ADMIN, "manage_frameworks"))
        self.assertTrue(can(ADMIN, "review_evidence"))
        self.assertTrue(can(MEMBER, "manage_evidence"))
        self.assertFalse(can(MEMBER, "review_evidence"))
        self.assertFalse(can(MEMBER, "manage_authorizations"))
        self.assertFalse(can(MEMBER, "audit_read"))
        self.assertTrue(can(VIEWER, "read"))
        self.assertFalse(can(VIEWER, "manage_systems"))

    def test_can_denies_none_and_unknown(self):
        """Core 9 RBAC. No user, unknown role, and unknown action are
        all denied by can()."""
        self.assertFalse(can(None, "read"))

        class Stranger:
            name = "mallory"
            role = "superuser"

        self.assertFalse(can(Stranger(), "read"))
        self.assertFalse(can(ADMIN, "no_such_action"))

    def test_require_passes_for_permitted(self):
        """Core 9 RBAC. require() returns True for a permitted action."""
        self.assertTrue(require(ADMIN, "admin"))
        self.assertTrue(require(MEMBER, "record_results"))
        self.assertTrue(require(VIEWER, "read"))

    def test_require_raises_for_denied(self):
        """Core 9 RBAC. require() raises PermissionDenied for a viewer
        mutation, a member overreach, no user, and an unknown action
        (admin included)."""
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "manage_findings")
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "manage_frameworks")
        with self.assertRaises(PermissionDenied):
            require(None, "read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "no_such_action")

    def test_permissions_for_unknown_role_is_empty(self):
        """Core 9 RBAC. permissions_for() of an unknown role grants
        nothing."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertEqual(permissions_for(None), set())


if __name__ == "__main__":
    unittest.main()
