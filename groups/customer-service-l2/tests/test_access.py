"""RBAC matrix (Core function 10; AC family, Low baseline)."""

import unittest

from custsvc.access import PERMISSIONS, can, require
from custsvc.errors import PermissionDenied

from custsvc_helpers import ADMIN, AGENT, VIEWER


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


if __name__ == "__main__":
    unittest.main()
