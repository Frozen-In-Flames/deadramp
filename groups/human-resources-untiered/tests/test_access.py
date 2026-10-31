"""RBAC tests.

Traces to: Core function 11 (Access control / RBAC, AC-3/AC-5/AC-6) --
the admin/hr_specialist/employee/auditor permission matrix in
``hr/access.py``.
"""

import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST
from hr.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from hr.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 11: RBAC -- exact permission matrix per role."""

    def test_admin_has_all_actions(self):
        """Core 11 (AC-3): admin holds every action incl. audit_read."""
        self.assertEqual(permissions_for("admin"), set(ACTIONS))

    def test_hr_specialist_writes_reads_reports_no_audit(self):
        """Core 11 (AC-6): hr_specialist holds all record reads + all record writes + report_read, but no audit_read."""
        perms = permissions_for("hr_specialist")
        for action in ACTIONS:
            if action == "audit_read":
                self.assertNotIn(action, perms)
            else:
                self.assertIn(action, perms)

    def test_employee_reads_only(self):
        """Core 11 (AC-6): employee holds record reads only -- no writes, no report_read, no audit_read."""
        perms = permissions_for("employee")
        self.assertTrue(all(a.endswith("_read") for a in perms))
        self.assertEqual(len(perms), 9)
        self.assertNotIn("report_read", perms)
        self.assertNotIn("audit_read", perms)

    def test_auditor_reads_plus_audit_no_writes(self):
        """Core 11 (AU-6): auditor holds all record reads + report_read + audit_read and no writes."""
        perms = permissions_for("auditor")
        self.assertIn("audit_read", perms)
        self.assertIn("report_read", perms)
        self.assertTrue(all(a.endswith("_read") for a in perms))

    def test_unknown_role_has_no_permissions(self):
        """Core 11 (AC-3): unknown role -> empty permission set."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(EMPLOYEE, "person_write"))

    def test_can_and_require(self):
        """Core 11: can()/require() agree with the matrix; require raises PermissionDenied."""
        self.assertTrue(can(ADMIN, "person_write"))
        self.assertTrue(require(SPECIALIST, "case_write"))
        with self.assertRaises(PermissionDenied):
            require(EMPLOYEE, "case_write")
        with self.assertRaises(PermissionDenied):
            require(None, "person_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "person_write")
        with self.assertRaises(PermissionDenied):
            require(SPECIALIST, "audit_read")

    def test_matrix_roles_exact(self):
        """Core 11: the matrix covers exactly the four spec roles."""
        self.assertEqual(set(PERMISSIONS), {"admin", "hr_specialist", "employee", "auditor"})


if __name__ == "__main__":
    unittest.main()
