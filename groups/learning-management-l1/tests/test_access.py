"""RBAC tests.

Traces to: Core function 13 (Access control / RBAC) -- the
admin/instructor/learner/auditor permission matrix in
``lms/access.py``: record reads are the thirteen ``*_read`` actions
(the L2 read set plus organization_read, certificate_read and
continuing_ed_read); instructor writes are registration/authorization/
plan/competency/progress/experience/workflow writes plus
certificate_write and continuing_ed_write; admin additionally holds
catalog_write, learner_write, compliance_write, organization_write
(admin-only), report_read and audit_read; learner holds record reads
only; auditor holds record reads + report_read + audit_read.
Control families: AC-2, AC-3, AC-6, IA-2.
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER
from lms.access import PERMISSIONS, User, can, permissions_for, require
from lms.errors import PermissionDenied

RECORD_READS = {
    "catalog_read",
    "learner_read",
    "registration_read",
    "authorization_read",
    "plan_read",
    "competency_read",
    "progress_read",
    "experience_read",
    "compliance_read",
    "workflow_read",
    "organization_read",
    "certificate_read",
    "continuing_ed_read",
}
INSTRUCTOR_WRITES = {
    "registration_write",
    "authorization_write",
    "plan_write",
    "competency_write",
    "progress_write",
    "experience_write",
    "workflow_write",
    "certificate_write",
    "continuing_ed_write",
}
ADMIN_ONLY_WRITES = {
    "catalog_write", "learner_write", "compliance_write", "organization_write",
}


class TestAccessMatrix(unittest.TestCase):
    """Core 13: RBAC -- exact permission matrix per role."""

    def test_admin_exact_set(self):
        """Core 13: admin = all record reads + all writes (incl. catalog/learner/compliance/organization) + report_read + audit_read, exactly."""
        expected = (
            RECORD_READS | INSTRUCTOR_WRITES | ADMIN_ONLY_WRITES
            | {"report_read", "audit_read"}
        )
        self.assertEqual(permissions_for("admin"), expected)
        self.assertEqual(PERMISSIONS["admin"], expected)

    def test_instructor_exact_set(self):
        """Core 13: instructor = record reads + instructor writes (incl. certificate_write and continuing_ed_write, but NOT organization_write) + report_read, exactly (no admin writes, no audit_read)."""
        expected = RECORD_READS | INSTRUCTOR_WRITES | {"report_read"}
        self.assertEqual(permissions_for("instructor"), expected)
        self.assertEqual(PERMISSIONS["instructor"], expected)

    def test_learner_exact_set(self):
        """Core 13: learner = record reads only, exactly -- no writes (incl. no certificate_write / continuing_ed_write / organization_write), no report_read, no audit_read."""
        self.assertEqual(permissions_for("learner"), set(RECORD_READS))
        self.assertEqual(PERMISSIONS["learner"], set(RECORD_READS))

    def test_auditor_exact_set(self):
        """Core 13: auditor = record reads + report_read + audit_read, exactly -- no writes."""
        expected = RECORD_READS | {"report_read", "audit_read"}
        self.assertEqual(permissions_for("auditor"), expected)
        self.assertEqual(PERMISSIONS["auditor"], expected)

    def test_matrix_roles_exact(self):
        """Core 13: the matrix covers exactly the four contract roles."""
        self.assertEqual(set(PERMISSIONS), {"admin", "instructor", "learner", "auditor"})

    def test_unknown_role_has_no_permissions(self):
        """Core 13: permissions_for() of an unknown role is the empty set."""
        self.assertEqual(permissions_for("superuser"), set())
        self.assertEqual(permissions_for(""), set())
        self.assertEqual(permissions_for(None), set())

    def test_can(self):
        """Core 13: can() agrees with the matrix for each role, including the L1 families: organization_write is admin-only, certificate_write and continuing_ed_write are instructor writes, and all three new reads are record reads."""
        self.assertTrue(can(ADMIN, "catalog_write"))
        self.assertTrue(can(ADMIN, "audit_read"))
        self.assertTrue(can(ADMIN, "organization_write"))
        self.assertTrue(can(INSTRUCTOR, "registration_write"))
        self.assertTrue(can(INSTRUCTOR, "report_read"))
        self.assertTrue(can(INSTRUCTOR, "certificate_write"))
        self.assertTrue(can(INSTRUCTOR, "continuing_ed_write"))
        self.assertFalse(can(INSTRUCTOR, "organization_write"))
        self.assertFalse(can(INSTRUCTOR, "catalog_write"))
        self.assertFalse(can(INSTRUCTOR, "compliance_write"))
        self.assertFalse(can(INSTRUCTOR, "audit_read"))
        self.assertTrue(can(LEARNER, "progress_read"))
        self.assertTrue(can(LEARNER, "organization_read"))
        self.assertTrue(can(LEARNER, "certificate_read"))
        self.assertTrue(can(LEARNER, "continuing_ed_read"))
        self.assertFalse(can(LEARNER, "progress_write"))
        self.assertFalse(can(LEARNER, "certificate_write"))
        self.assertFalse(can(LEARNER, "continuing_ed_write"))
        self.assertFalse(can(LEARNER, "organization_write"))
        self.assertFalse(can(LEARNER, "report_read"))
        self.assertTrue(can(AUDITOR, "audit_read"))
        self.assertTrue(can(AUDITOR, "organization_read"))
        self.assertFalse(can(AUDITOR, "workflow_write"))
        self.assertFalse(can(AUDITOR, "organization_write"))
        self.assertFalse(can(None, "catalog_read"))

    def test_require(self):
        """Core 13: require() returns True when permitted and raises PermissionDenied for an unknown user, an unknown role, and an action outside the role's set (incl. organization_write for an instructor)."""
        self.assertTrue(require(ADMIN, "learner_write"))
        self.assertTrue(require(ADMIN, "organization_write"))
        self.assertTrue(require(INSTRUCTOR, "plan_write"))
        self.assertTrue(require(INSTRUCTOR, "certificate_write"))
        self.assertTrue(require(INSTRUCTOR, "continuing_ed_write"))
        with self.assertRaises(PermissionDenied):
            require(LEARNER, "plan_write")
        with self.assertRaises(PermissionDenied):
            require(INSTRUCTOR, "organization_write")
        with self.assertRaises(PermissionDenied):
            require(None, "catalog_read")
        with self.assertRaises(PermissionDenied):
            require(User("mallory", "superuser"), "catalog_read")
        with self.assertRaises(PermissionDenied):
            require(ADMIN, "teleport_write")
        with self.assertRaises(PermissionDenied):
            require(AUDITOR, "registration_write")


if __name__ == "__main__":
    unittest.main()
