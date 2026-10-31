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
        """Core 9 [L3] (AC-5/AU-6): auditor holds audit_read ONLY -- at L3 the L2 record reads and report_read are removed (separation of duties: audit review is a standalone duty)."""
        perms = permissions_for("auditor")
        self.assertEqual(perms, {"audit_read"})
        self.assertNotIn("report_read", perms)

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


class TestAuditorRole(unittest.TestCase):
    """Core 9 [L3] (AC-5): the auditor role holds audit_read ONLY --
    separation of duties: audit review exists as a duty separable
    from administration, clinical work, and every operational
    permission."""

    def test_auditor_matrix_is_audit_read_only(self):
        """AC-5: PERMISSIONS["auditor"] == {"audit_read"} exactly."""
        self.assertEqual(PERMISSIONS["auditor"], {"audit_read"})

    def test_auditor_can_read_audit(self):
        """AC-5: require(auditor, "audit_read") passes."""
        self.assertTrue(require(AUDITOR, "audit_read"))
        self.assertTrue(can(AUDITOR, "audit_read"))

    def test_auditor_cannot_read_records_or_reports(self):
        """AC-5: the auditor holds no operational read -- none of the
        7 record reads and no report_read."""
        for action in ("participant_read", "program_read", "enrollment_read",
                       "measurement_read", "plan_read", "activity_read",
                       "eligibility_read", "report_read"):
            self.assertFalse(can(AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(AUDITOR, action)

    def test_auditor_cannot_write_anything(self):
        """AC-5: the auditor holds no write permission at all."""
        for action in ("participant_write", "program_write", "enrollment_write",
                       "measurement_write", "plan_write", "activity_write",
                       "eligibility_write"):
            self.assertFalse(can(AUDITOR, action), action)
            with self.assertRaises(PermissionDenied):
                require(AUDITOR, action)

    def test_existing_roles_unchanged_by_tightening(self):
        """AC-5: tightening the auditor moved no other permission --
        admin still holds all 16, clinician/member matrices intact."""
        self.assertEqual(permissions_for("admin"), set(ACTIONS))
        self.assertEqual(len(permissions_for("clinician")), 12)
        self.assertEqual(len(permissions_for("member")), 7)


if __name__ == "__main__":
    unittest.main()
