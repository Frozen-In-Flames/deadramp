"""RBAC tests.

Traces to: Core function 9 (Access control / RBAC, AC-3/AC-5/AC-6) --
the admin/instructor/learner/auditor permission matrix in
``learn/access.py``.
"""

import unittest

from learn_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER
from learn.access import PERMISSIONS, can, permissions_for, require
from learn.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 9: RBAC -- exact permission matrix per role."""

    def test_admin_has_all_actions(self):
        """Core 9 (AC-3): admin holds every action incl. audit_read."""
        from learn.access import ACTIONS
        self.assertEqual(permissions_for("admin"), set(ACTIONS))

    def test_instructor_writes_and_reads(self):
        """Core 9 (AC-6): instructor writes enrollments/progress/assessments/sessions, reads records + reports, but no catalog/credential/compliance writes and no audit_read."""
        perms = permissions_for("instructor")
        for action in ("enrollment_write", "progress_write", "assessment_write", "schedule_write",
                       "catalog_read", "report_read"):
            self.assertIn(action, perms)
        for action in ("catalog_write", "credential_write", "compliance_write", "audit_read"):
            self.assertNotIn(action, perms)

    def test_learner_reads_only(self):
        """Core 9 (AC-6): learner holds record reads only -- no writes, no report_read, no audit_read."""
        perms = permissions_for("learner")
        self.assertTrue(all(a.endswith("_read") for a in perms))
        self.assertNotIn("report_read", perms)
        self.assertNotIn("audit_read", perms)

    def test_auditor_reads_plus_audit_no_writes(self):
        """Core 9 (AU-6): auditor holds all record reads + report_read + audit_read and no writes."""
        perms = permissions_for("auditor")
        self.assertIn("audit_read", perms)
        self.assertIn("report_read", perms)
        self.assertTrue(all(a.endswith("_read") for a in perms))

    def test_unknown_role_has_no_permissions(self):
        """Core 9 (AC-3): unknown role -> empty permission set."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(LEARNER, "catalog_write"))

    def test_can_and_require(self):
        """Core 9: can()/require() agree with the matrix; require raises PermissionDenied."""
        self.assertTrue(can(ADMIN, "catalog_write"))
        self.assertTrue(require(INSTRUCTOR, "progress_write"))
        with self.assertRaises(PermissionDenied):
            require(LEARNER, "progress_write")
        with self.assertRaises(PermissionDenied):
            require(None, "catalog_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "enrollment_write")

    def test_matrix_roles_exact(self):
        """Core 9: the matrix covers exactly the four spec roles."""
        self.assertEqual(set(PERMISSIONS), {"admin", "instructor", "learner", "auditor"})


if __name__ == "__main__":
    unittest.main()
