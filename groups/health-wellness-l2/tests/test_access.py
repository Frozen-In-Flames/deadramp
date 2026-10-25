"""RBAC tests.

Traces to: Core function 9 (Access control / RBAC, AC-3/AC-5/AC-6) --
the admin/clinician/member/auditor permission matrix in
``health/access.py``. RBAC is baseline-carried, not claimed (0/5).
"""

import unittest

from health_helpers import ADMIN, AUDITOR, CLINICIAN, MEMBER
from health.access import ACTIONS, PERMISSIONS, can, permissions_for, require
from health.errors import PermissionDenied


class TestAccessMatrix(unittest.TestCase):
    """Core 9: RBAC -- exact permission matrix per role."""

    def test_admin_has_all_actions(self):
        """Core 9 (AC-3): admin holds every action incl. audit_read (all 16)."""
        self.assertEqual(len(ACTIONS), 16)
        self.assertEqual(permissions_for("admin"), set(ACTIONS))

    def test_clinician_writes_and_reads(self):
        """Core 9 (AC-6): clinician holds all 7 record reads + enrollment/measurement/plan/activity writes + report_read; no participant/program/eligibility writes, no audit_read."""
        perms = permissions_for("clinician")
        for action in ("enrollment_write", "measurement_write", "plan_write",
                       "activity_write", "participant_read", "report_read"):
            self.assertIn(action, perms)
        for action in ("participant_write", "program_write", "eligibility_write",
                       "audit_read"):
            self.assertNotIn(action, perms)

    def test_member_reads_only(self):
        """Core 9 (AC-6): member holds the 7 record reads only -- no writes, no report_read, no audit_read."""
        perms = permissions_for("member")
        self.assertEqual(len(perms), 7)
        self.assertTrue(all(a.endswith("_read") for a in perms))
        self.assertNotIn("report_read", perms)
        self.assertNotIn("audit_read", perms)

    def test_auditor_reads_plus_audit_no_writes(self):
        """Core 9 (AU-6): auditor holds all 7 record reads + report_read + audit_read and no writes."""
        perms = permissions_for("auditor")
        self.assertIn("audit_read", perms)
        self.assertIn("report_read", perms)
        self.assertTrue(all(a.endswith("_read") for a in perms))

    def test_unknown_role_has_no_permissions(self):
        """Core 9 (AC-3): unknown role -> empty permission set."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertFalse(can(MEMBER, "participant_write"))

    def test_can_and_require(self):
        """Core 9: can()/require() agree with the matrix; require raises PermissionDenied."""
        self.assertTrue(can(ADMIN, "participant_write"))
        self.assertTrue(require(CLINICIAN, "measurement_write"))
        with self.assertRaises(PermissionDenied):
            require(MEMBER, "measurement_write")
        with self.assertRaises(PermissionDenied):
            require(None, "participant_read")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "enrollment_write")

    def test_matrix_roles_exact(self):
        """Core 9: the matrix covers exactly the four spec roles."""
        self.assertEqual(set(PERMISSIONS), {"admin", "clinician", "member", "auditor"})


if __name__ == "__main__":
    unittest.main()
