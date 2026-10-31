"""Access-control tests.

Traces to: Core function 9 (RBAC — role permission matrix enforced on
every operation, admin/member/viewer granularity); control family
AC-3 / AC-6 (access enforcement, least privilege) and IA-2 (identity
is supplied by the embedding organization; these are hooks, not an
IdP). [L3] adds the auditor role (AC-5 separation of duties).
"""

import unittest

from grc_helpers import ADMIN, AUDITOR, MEMBER, VIEWER
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

    def test_roles_are_admin_member_viewer_auditor(self):
        """Core 9 RBAC [L3]. The role set is exactly
        admin/member/viewer/auditor: the L2 three plus the auditor
        role added by the High uplift (AC-5)."""
        self.assertEqual(set(ROLES), {"admin", "member", "viewer", "auditor"})
        self.assertEqual(
            set(PERMISSIONS), {"admin", "member", "viewer", "auditor"})

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


class TestAuditorRole(unittest.TestCase):
    """Core 9 RBAC [L3] (AC-5 separation of duties): the auditor
    role holds audit_read and nothing else — audit review exists as
    a duty separable from administration and from operations."""

    def test_auditor_matrix_is_audit_read_only(self):
        """AC-5. The auditor permission set is exactly {audit_read}."""
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})
        self.assertEqual(permissions_for("auditor"), {"audit_read"})

    def test_auditor_can_read_audit(self):
        """AC-5 / AU-6. The auditor may perform audit_read."""
        self.assertTrue(can(AUDITOR, "audit_read"))
        self.assertTrue(require(AUDITOR, "audit_read"))

    def test_auditor_cannot_read_records(self):
        """AC-5. The auditor holds no operational read: not even the
        plain "read" action every other role holds."""
        self.assertFalse(can(AUDITOR, "read"))

    def test_auditor_cannot_manage_anything(self):
        """AC-5. Every manage_* / record / review / admin action is
        denied to the auditor."""
        for action in (
            "manage_frameworks",
            "manage_systems",
            "manage_indicators",
            "record_results",
            "manage_evidence",
            "review_evidence",
            "manage_findings",
            "manage_assessments",
            "manage_authorizations",
            "admin",
        ):
            self.assertFalse(can(AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(AUDITOR, action)

    def test_existing_roles_unchanged_by_auditor(self):
        """AC-5. Adding the auditor moved no existing permission:
        member still lacks audit_read, viewer is still read-only,
        admin still holds all 12 actions."""
        self.assertFalse(can(MEMBER, "audit_read"))
        self.assertEqual(PERMISSIONS["viewer"], {"read"})
        self.assertEqual(len(PERMISSIONS["admin"]), 12)


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
