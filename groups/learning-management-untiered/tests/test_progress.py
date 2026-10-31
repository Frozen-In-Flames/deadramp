"""Learner progress & readiness record tests.

Traces to: Core function 7 (Progress & readiness records) --
record_progress (``prg-``) with statuses not_started|in_progress|
completed, readiness not_ready|developing|ready, and percent_complete
a number in 0..100 (bool rejected). A completed record is what the
compliance derivation reads (Core function 9). Learner scope applies
under Core function 12.
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestProgress(unittest.TestCase):
    """Core 7: progress/readiness records per learner+course."""

    def test_record_progress_shape(self):
        """Core 7: a progress record carries prg- id, learner_ref, course, status, readiness, percent and provenance."""
        store, _, course = make_store()
        rec = store.record_progress(
            "carol", course["id"], "in_progress", INSTRUCTOR,
            readiness="developing", percent_complete=40, note="halfway",
        )
        self.assertEqual(rec["id"], "prg-1")
        self.assertEqual(rec["learner_ref"], "carol")
        self.assertEqual(rec["course_id"], course["id"])
        self.assertEqual(rec["status"], "in_progress")
        self.assertEqual(rec["readiness"], "developing")
        self.assertEqual(rec["percent_complete"], 40)
        self.assertEqual(rec["note"], "halfway")
        self.assertEqual(rec["recorded_by"], "bob")
        self.assertIn("recorded_utc", rec)
        bare = store.record_progress("carol", course["id"], "not_started", INSTRUCTOR)
        self.assertIsNone(bare["readiness"])
        self.assertIsNone(bare["percent_complete"])

    def test_statuses_and_percent_bounds(self):
        """Core 7: all three statuses record; percent bounds 0 and 100 (and fractional percents) are accepted."""
        store, _, course = make_store()
        for status in ("not_started", "in_progress", "completed"):
            rec = store.record_progress("carol", course["id"], status, INSTRUCTOR)
            self.assertEqual(rec["status"], status)
        for percent in (0, 100, 55.5):
            rec = store.record_progress("carol", course["id"], "in_progress",
                                        INSTRUCTOR, percent_complete=percent)
            self.assertEqual(rec["percent_complete"], percent)
        listed = store.list_progress(ADMIN, learner_ref="carol", course_id=course["id"])
        self.assertEqual(len(listed), 6)

    def test_validation(self):
        """Core 7: bad status/readiness, percent >100/<0/bool/string all -> ValidationError; unknown learner or course -> NotFoundError; failed records consume no id."""
        store, _, course = make_store()
        with self.assertRaises(ValidationError):
            store.record_progress("carol", course["id"], "done", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR,
                                  readiness="great")
        for bad_percent in (101, -1, True, False, "50"):
            with self.subTest(percent_complete=bad_percent):
                with self.assertRaises(ValidationError):
                    store.record_progress("carol", course["id"], "in_progress",
                                          INSTRUCTOR, percent_complete=bad_percent)
        with self.assertRaises(NotFoundError):
            store.record_progress("ghost", course["id"], "in_progress", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.record_progress("carol", "crs-999", "in_progress", INSTRUCTOR)
        rec = store.record_progress("carol", course["id"], "not_started", INSTRUCTOR)
        self.assertEqual(rec["id"], "prg-1")

    def test_learner_cannot_record_and_scope(self):
        """Core 7 / Core 12: a learner may not record progress; a learner reads her own records only."""
        store, _, course = make_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.record_progress("carol", course["id"], "completed", LEARNER)
        own = store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        other = store.record_progress("erin", course["id"], "in_progress", INSTRUCTOR)
        self.assertEqual(store.get_progress(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_progress(other["id"], LEARNER)
        self.assertEqual([r["id"] for r in store.list_progress(LEARNER)], [own["id"]])
        with self.assertRaises(NotFoundError):
            store.get_progress("prg-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
