"""Enrollment tests.

Traces to: Core function 3 (Enrollments with derived status;
AC-2, AU-2, CA-7) -- enrollment/registration records binding a
participant to a program, with status derived deterministically from
the participant's plan records for that program.
"""

import unittest

from health_helpers import ADMIN, CLINICIAN, MEMBER, make_store
from health.errors import NotFoundError, PermissionDenied, ValidationError

AS_OF = "2026-06-15"


class TestEnrollments(unittest.TestCase):
    """Core 3: enrollments and derived-status precedence overdue > completed > enrolled."""

    def test_create_shape_and_view(self):
        """Core 3: created enrollment stores status 'enrolled' with an enr- id; the read view adds derived_status 'enrolled' when no plans exist."""
        store, program, participant = make_store()
        enr = store.create_enrollment(participant["id"], program["id"], CLINICIAN)
        self.assertEqual(enr["id"], "enr-1")
        self.assertEqual(enr["status"], "enrolled")
        view = store.get_enrollment(enr["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(view["derived_status"], "enrolled")

    def test_registration_kind_and_duplicate_rejected(self):
        """Core 3: registration kind accepted; duplicate active enrollment (same participant+program+kind) -> ValidationError with no id consumed; a different kind is a distinct enrollment."""
        store, program, participant = make_store()
        store.create_enrollment(participant["id"], program["id"], ADMIN)
        with self.assertRaises(ValidationError):
            store.create_enrollment(participant["id"], program["id"], ADMIN)
        reg = store.create_enrollment(participant["id"], program["id"], ADMIN,
                                      kind="registration")
        self.assertEqual(reg["id"], "enr-2")
        self.assertEqual(reg["kind"], "registration")

    def test_unknown_refs_and_validation(self):
        """Core 3 (SI-10): unknown participant/program -> NotFoundError; bad kind -> ValidationError."""
        store, program, participant = make_store()
        with self.assertRaises(NotFoundError):
            store.create_enrollment("par-999", program["id"], ADMIN)
        with self.assertRaises(NotFoundError):
            store.create_enrollment(participant["id"], "prg-999", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_enrollment(participant["id"], program["id"], ADMIN, kind="alien")

    def test_derived_completed_and_overdue_precedence(self):
        """Core 3 (CA-7): a completed plan for the program -> derived completed; an additional overdue plan -> derived overdue (overdue wins); plans in other programs do not affect the derivation."""
        store, program, participant = make_store()
        other_prog = store.create_program("Other", ADMIN)
        enr = store.create_enrollment(participant["id"], program["id"], ADMIN)
        plan = store.create_plan(participant["id"], program["id"], "Goal",
                                 "2026-06-01", CLINICIAN)
        store.complete_plan(plan["id"], "2026-05-20", CLINICIAN)
        self.assertEqual(store.get_enrollment(enr["id"], ADMIN, as_of=AS_OF)["derived_status"],
                         "completed")
        late = store.create_plan(participant["id"], program["id"], "Late goal",
                                 "2026-06-01", CLINICIAN)
        self.assertEqual(store.get_enrollment(enr["id"], ADMIN, as_of=AS_OF)["derived_status"],
                         "overdue")
        self.assertEqual(store.get_enrollment(enr["id"], ADMIN, as_of="2026-05-01")["derived_status"],
                         "completed")
        # A plan in another program is irrelevant to this enrollment.
        store.create_plan(participant["id"], other_prog["id"], "Elsewhere",
                          "2026-01-01", CLINICIAN)
        other_enr = store.create_enrollment(participant["id"], other_prog["id"], ADMIN)
        self.assertEqual(store.get_enrollment(other_enr["id"], ADMIN, as_of=AS_OF)["derived_status"],
                         "overdue")

    def test_member_scope_and_filters(self):
        """Core 3 + member scope: member reads own enrollment, is denied another participant's, lists exclude others; filters by participant_id/program_id work; member write denied, clinician write allowed."""
        store, program, participant = make_store()
        other = store.create_participant("erin", ADMIN)
        own = store.create_enrollment(participant["id"], program["id"], CLINICIAN)
        other_enr = store.create_enrollment(other["id"], program["id"], CLINICIAN)
        self.assertEqual(store.get_enrollment(own["id"], MEMBER, as_of=AS_OF)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_enrollment(other_enr["id"], MEMBER, as_of=AS_OF)
        with self.assertRaises(PermissionDenied):
            store.list_enrollments(MEMBER, participant_id=other["id"], as_of=AS_OF)
        listing = store.list_enrollments(MEMBER, as_of=AS_OF)
        self.assertEqual([r["id"] for r in listing], [own["id"]])
        filtered = store.list_enrollments(ADMIN, program_id=program["id"], as_of=AS_OF)
        self.assertEqual(len(filtered), 2)
        with self.assertRaises(PermissionDenied):
            store.create_enrollment(other["id"], program["id"], MEMBER, kind="registration")


if __name__ == "__main__":
    unittest.main()
