"""Access control (RBAC) tests.

Traces to: Core 10 (Access control / RBAC) and control families
AC-3, AC-6 -- the exact 14-action permission matrix for
admin/operator/viewer, plus [L3] the AC-5 auditor role.
"""

import unittest

import crm_helpers as H
from crm.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from crm.errors import PermissionDenied

READS = {
    "registry_read", "case_read", "interaction_read", "guide_read",
    "finding_read", "config_read", "report_read",
}
OPERATOR_WRITES = {
    "registry_write", "case_write", "interaction_write",
    "guide_write", "finding_write",
}


class TestMatrix(unittest.TestCase):
    """Core 10: the permission matrix is exactly as contracted."""

    def test_action_count(self):
        """Core 10: 14 actions total."""
        self.assertEqual(len(ACTIONS), 14)
        self.assertEqual(len(set(ACTIONS)), 14)

    def test_admin_has_everything(self):
        """Core 10: admin holds all 14 actions incl. config_write + audit_read."""
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))

    def test_operator_matrix(self):
        """Core 10: operator = all reads except audit_read + operational writes;
        NOT config_write, NOT audit_read."""
        self.assertEqual(PERMISSIONS["operator"], READS | OPERATOR_WRITES)
        self.assertNotIn("config_write", PERMISSIONS["operator"])
        self.assertNotIn("audit_read", PERMISSIONS["operator"])

    def test_viewer_matrix(self):
        """Core 10: viewer = reads only, except audit_read."""
        self.assertEqual(PERMISSIONS["viewer"], READS)
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])

    def test_roles_are_exactly_four(self):
        """Core 10 [L3]: ROLES is exactly admin/operator/viewer/auditor."""
        from crm.access import ROLES
        self.assertEqual(set(ROLES), {"admin", "operator", "viewer", "auditor"})
        self.assertEqual(set(PERMISSIONS), {"admin", "operator", "viewer", "auditor"})

    def test_permissions_for_unknown_role_empty(self):
        """Core 10 (AC-6): unknown roles hold no permissions."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertEqual(permissions_for(None), set())


class TestCanRequire(unittest.TestCase):
    """Core 10: can()/require() semantics."""

    def test_can(self):
        """Core 10: can() reflects the matrix; None user cannot."""
        self.assertTrue(can(H.ADMIN, "config_write"))
        self.assertFalse(can(H.OPERATOR, "config_write"))
        self.assertFalse(can(H.VIEWER, "case_write"))
        self.assertFalse(can(None, "case_read"))

    def test_require_ok(self):
        """Core 10: require() returns True when permitted."""
        self.assertTrue(require(H.ADMIN, "audit_read"))
        self.assertTrue(require(H.VIEWER, "case_read"))

    def test_require_denied(self):
        """Core 10 (AC-3): require() raises PermissionDenied when not
        permitted, for None users, and for unknown roles/actions."""
        with self.assertRaises(PermissionDenied):
            require(H.VIEWER, "case_write")
        with self.assertRaises(PermissionDenied):
            require(None, "case_read")
        from crm.access import User
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "case_read")
        with self.assertRaises(PermissionDenied):
            require(H.ADMIN, "not_an_action")


class TestAuditorRole(unittest.TestCase):
    """Core 10 [L3] (AC-5): the auditor role holds audit_read ONLY --
    separation of duties: audit review exists as a duty separable
    from administration and from every operational permission."""

    def test_auditor_matrix_is_audit_read_only(self):
        """AC-5: PERMISSIONS["auditor"] == {"audit_read"} exactly."""
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})

    def test_auditor_can_read_audit(self):
        """AC-5: require(auditor, "audit_read") passes."""
        self.assertTrue(require(H.AUDITOR, "audit_read"))
        self.assertTrue(can(H.AUDITOR, "audit_read"))

    def test_auditor_cannot_read_registry_or_cases(self):
        """AC-5: the auditor holds no operational read."""
        for action in ("registry_read", "case_read", "interaction_read",
                       "guide_read", "finding_read", "config_read",
                       "report_read"):
            self.assertFalse(can(H.AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(H.AUDITOR, action)

    def test_auditor_cannot_write_anything(self):
        """AC-5: the auditor holds no write permission at all."""
        for action in ("registry_write", "case_write", "interaction_write",
                       "guide_write", "finding_write", "config_write"):
            self.assertFalse(can(H.AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(H.AUDITOR, action)

    def test_existing_roles_unchanged_by_auditor(self):
        """AC-5: adding the auditor moved no existing permission --
        admin still holds all 14, operator/viewer matrices intact."""
        self.assertEqual(PERMISSIONS["admin"], set(ACTIONS))
        self.assertEqual(PERMISSIONS["operator"], READS | OPERATOR_WRITES)
        self.assertEqual(PERMISSIONS["viewer"], READS)


if __name__ == "__main__":
    unittest.main()
