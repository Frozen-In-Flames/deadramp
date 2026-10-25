"""Learner progress & readiness record tests.

Traces to: Core function 3 (Learner progress & readiness records;
claim family learner_progress 0/2 in this group, carried under the
core-boundary decision (2/8 at L2); AU-2). Completion is the
terminal progress state, recorded as a record -- no content delivery.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestProgress(unittest.TestCase):
    """Core 3: progress/readiness records per learner+course."""

    def test_record_progress_shape(self):
        """Core 3: a progress record carries prg- id, status, readiness, percent and provenance."""
        store, course = make_store()
        rec = store.record_progress(
            "carol", course["id"], "in_progress", INSTRUCTOR,
            readiness="developing", percent_complete=40,
        )
        self.assertEqual(rec["id"], "prg-1")
        self.assertEqual(rec["status"], "in_progress")
        self.assertEqual(rec["readiness"], "developing")
        self.assertEqual(rec["percent_complete"], 40)
        self.assertEqual(rec["recorded_by"], "bob")

    def test_completion_is_terminal_state_record(self):
        """Core 3: 'completed' is recorded as a progress state (the record form tracking presupposes)."""
        store, course = make_store()
        store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR)
        done = store.record_progress("carol", course["id"], "completed", INSTRUCTOR, readiness="ready")
        self.assertEqual(done["status"], "completed")
        listed = store.list_progress(ADMIN, learner_id="carol", course_id=course["id"])
        self.assertEqual([r["status"] for r in listed], ["in_progress", "completed"])

    def test_validation(self):
        """Core 3 (SI-10): bad status/readiness/percent rejected; unknown course -> NotFoundError; no id consumed."""
        store, course = make_store()
        with self.assertRaises(ValidationError):
            store.record_progress("carol", course["id"], "done", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR, readiness="great")
        with self.assertRaises(ValidationError):
            store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR, percent_complete=101)
        with self.assertRaises(NotFoundError):
            store.record_progress("carol", "crs-999", "in_progress", INSTRUCTOR)
        rec = store.record_progress("carol", course["id"], "not_started", INSTRUCTOR)
        self.assertEqual(rec["id"], "prg-1")

    def test_learner_cannot_record_and_scope(self):
        """Core 3 / Core 9: learner may not record progress; learner reads own records only."""
        store, course = make_store()
        with self.assertRaises(PermissionDenied):
            store.record_progress("carol", course["id"], "completed", LEARNER)
        own = store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        other = store.record_progress("erin", course["id"], "in_progress", INSTRUCTOR)
        self.assertEqual(store.get_progress(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_progress(other["id"], LEARNER)
        self.assertEqual([r["id"] for r in store.list_progress(LEARNER)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
