"""RBAC matrix (Core function 10; AC family, High baseline [L3])."""

import unittest

from custsvc.access import PERMISSIONS, can, require
from custsvc.errors import PermissionDenied

from custsvc_helpers import ADMIN, AGENT, AUDITOR, VIEWER


class TestAccessMatrix(unittest.TestCase):
    def test_admin_has_everything(self):
        for action in PERMISSIONS["admin"]:
            self.assertTrue(can(ADMIN, action), action)
        self.assertIn("rule_write", PERMISSIONS["admin"])
        self.assertIn("audit_read", PERMISSIONS["admin"])

    def test_agent_writes_but_no_rules_or_audit(self):
        for action in ("case_write", "requester_write", "responder_write",
                       "alert_write", "schedule_write"):
            self.assertTrue(can(AGENT, action), action)
        self.assertFalse(can(AGENT, "rule_write"))
        self.assertFalse(can(AGENT, "audit_read"))
        self.assertTrue(can(AGENT, "case_read"))
        self.assertTrue(can(AGENT, "report_read"))

    def test_viewer_reads_only_no_audit(self):
        self.assertTrue(can(VIEWER, "case_read"))
        self.assertFalse(can(VIEWER, "case_write"))
        self.assertFalse(can(VIEWER, "audit_read"))
        self.assertFalse(can(VIEWER, "rule_write"))

    def test_require_raises_for_denied(self):
        with self.assertRaises(PermissionDenied):
            require(VIEWER, "case_write")
        with self.assertRaises(PermissionDenied):
            require(None, "case_read")
        with self.assertRaises(PermissionDenied):
            require(AGENT, "audit_read")

    def test_unknown_role_gets_nothing(self):
        from custsvc.access import User
        ghost = User(name="mallory", role="superuser")
        self.assertFalse(can(ghost, "case_read"))
        with self.assertRaises(PermissionDenied):
            require(ghost, "case_read")



class TestAuditorRole(unittest.TestCase):
    """[L3] AC-5: the auditor role holds audit_read and nothing else."""

    def test_auditor_permissions_are_exactly_audit_read(self):
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})

    def test_auditor_can_read_audit(self):
        self.assertTrue(can(AUDITOR, "audit_read"))
        self.assertTrue(require(AUDITOR, "audit_read"))

    def test_auditor_cannot_read_registry(self):
        for action in ("case_read", "requester_read", "responder_read",
                       "alert_read", "schedule_read", "rule_read",
                       "report_read"):
            self.assertFalse(can(AUDITOR, action), action)

    def test_auditor_cannot_write_anything(self):
        for action in ("case_write", "requester_write", "responder_write",
                       "alert_write", "schedule_write", "rule_write"):
            self.assertFalse(can(AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(AUDITOR, action)

    def test_existing_roles_unchanged_by_auditor(self):
        # The uplift adds a role; it does not move anyone else's
        # permissions (Merge Rule: no dilution, no sideways grants).
        self.assertNotIn("audit_read", PERMISSIONS["agent"])
        self.assertNotIn("audit_read", PERMISSIONS["viewer"])
        self.assertIn("audit_read", PERMISSIONS["admin"])

    def test_role_set_is_exactly_four(self):
        from custsvc.access import ROLES
        self.assertEqual(set(ROLES), {"admin", "agent", "viewer", "auditor"})


if __name__ == "__main__":
    unittest.main()
