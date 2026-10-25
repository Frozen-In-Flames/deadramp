"""Scheduling record tests.

Traces to: Core function 7 (Scheduling records for training/
assessment sessions; claim family scheduling 0/2 in this group,
carried under the core-boundary decision (2/8 at L2); AU-2, CM-6).
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestScheduling(unittest.TestCase):
    """Core 7: scheduled session records bound to registry entries."""

    def test_create_session_record(self):
        """Core 7 (CM-6): a session record binds title, course, kind, ISO times and learner ids with a sch- id."""
        store, course = make_store()
        session = store.create_session(
            "Safety Session 1", course["id"], "2026-07-01T09:00:00Z", INSTRUCTOR,
            ends_at="2026-07-01T11:00:00Z", kind="training",
            location="Room 4", learner_ids=["carol", "erin"],
        )
        self.assertEqual(session["id"], "sch-1")
        self.assertEqual(session["kind"], "training")
        self.assertEqual(session["learner_ids"], ["carol", "erin"])
        assessment_session = store.create_session(
            "Exam Slot", course["id"], "2026-07-02T09:00:00Z", INSTRUCTOR, kind="assessment",
        )
        self.assertEqual(assessment_session["kind"], "assessment")

    def test_session_binds_assessment_record(self):
        """Core 7 / Core 4: an assessment record can reference a scheduled session by id."""
        store, course = make_store()
        session = store.create_session(
            "Exam Slot", course["id"], "2026-07-02T09:00:00Z", INSTRUCTOR, kind="assessment",
        )
        rec = store.create_assessment("Safety Quiz", "carol", INSTRUCTOR,
                                      course_id=course["id"], session_id=session["id"])
        self.assertEqual(rec["session_id"], session["id"])

    def test_validation(self):
        """Core 7 (SI-10): ends before starts, bad kind and malformed datetime rejected; unknown course -> NotFoundError."""
        store, course = make_store()
        with self.assertRaises(ValidationError):
            store.create_session("S", course["id"], "2026-07-01T11:00:00Z", INSTRUCTOR,
                                 ends_at="2026-07-01T09:00:00Z")
        with self.assertRaises(ValidationError):
            store.create_session("S", course["id"], "2026-07-01T09:00:00Z", INSTRUCTOR, kind="party")
        with self.assertRaises(ValidationError):
            store.create_session("S", course["id"], "next Tuesday", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.create_session("S", "crs-999", "2026-07-01T09:00:00Z", INSTRUCTOR)

    def test_schedule_write_roles_and_list_filter(self):
        """Core 7 / Core 9: instructor and admin may schedule; learner may not; list filters by course."""
        store, course = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_session("S", course["id"], "2026-07-01T09:00:00Z", LEARNER)
        store.create_session("S", course["id"], "2026-07-01T09:00:00Z", INSTRUCTOR)
        self.assertEqual(len(store.list_sessions(ADMIN, course_id=course["id"])), 1)
        self.assertEqual(len(store.list_sessions(LEARNER)), 1)
        self.assertEqual(store.list_sessions(ADMIN, course_id="crs-999"), [])


if __name__ == "__main__":
    unittest.main()
