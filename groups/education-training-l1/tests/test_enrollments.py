"""Enrollment & registration tests.

Traces to: Core function 2 (Enrollments & candidate registrations;
claim family enrollment_registration 0/2 in this group, carried
under the core-boundary decision (2/8 at L2); AC-2, AU-2), plus learner
scope under Core function 9.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestEnrollments(unittest.TestCase):
    """Core 2: enrollment/registration records binding learner to registry entry."""

    def test_create_enrollment_and_registration(self):
        """Core 2 (AC-2): enrollment and candidate-registration kinds both record against a course."""
        store, course = make_store()
        enr = store.create_enrollment("carol", course["id"], INSTRUCTOR)
        reg = store.create_enrollment("erin", course["id"], ADMIN, kind="registration")
        self.assertEqual(enr["id"], "enr-1")
        self.assertEqual(enr["status"], "enrolled")
        self.assertEqual(reg["kind"], "registration")
        self.assertEqual(reg["learner_id"], "erin")

    def test_duplicate_enrollment_rejected(self):
        """Core 2 (SI-10): a duplicate active enrollment for the same learner+course+kind is a validation error and consumes no id."""
        store, course = make_store()
        store.create_enrollment("carol", course["id"], INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.create_enrollment("carol", course["id"], INSTRUCTOR)
        nxt = store.create_enrollment("erin", course["id"], INSTRUCTOR)
        self.assertEqual(nxt["id"], "enr-2")

    def test_unknown_course_not_found(self):
        """Core 2: enrolling against an unknown course -> NotFoundError."""
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_enrollment("carol", "crs-999", INSTRUCTOR)

    def test_learner_write_denied(self):
        """Core 2 / Core 9: a learner may not create enrollments."""
        store, course = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_enrollment("carol", course["id"], LEARNER)

    def test_learner_scope_reads(self):
        """Core 2 / Core 9: a learner reads her own enrollment, is denied another learner's, and lists only her own."""
        store, course = make_store()
        own = store.create_enrollment("carol", course["id"], INSTRUCTOR)
        other = store.create_enrollment("erin", course["id"], INSTRUCTOR)
        self.assertEqual(store.get_enrollment(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_enrollment(other["id"], LEARNER)
        with self.assertRaises(PermissionDenied):
            store.list_enrollments(LEARNER, learner_id="erin")
        listed = store.list_enrollments(LEARNER)
        self.assertEqual([e["id"] for e in listed], [own["id"]])

    def test_list_filters(self):
        """Core 2: list filters by learner_id and course_id for staff roles."""
        store, course = make_store()
        store.create_enrollment("carol", course["id"], INSTRUCTOR)
        store.create_enrollment("erin", course["id"], INSTRUCTOR)
        self.assertEqual(len(store.list_enrollments(ADMIN, learner_id="carol")), 1)
        self.assertEqual(len(store.list_enrollments(ADMIN, course_id=course["id"])), 2)


if __name__ == "__main__":
    unittest.main()
