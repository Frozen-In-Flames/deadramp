"""Assessment record tests.

Traces to: Core function 4 (Assessment records -- delivery/
administration records; claim family assessments 0/2 in this group,
carried under the core-boundary decision (2/8 at L2); AU-2, AU-3,
SI-10). Records only: there is NO scoring in the Core (deterministic
scoring is Extended, 0 claims in either tier of this category), and
these tests assert responses are
stored verbatim with no score field ever appearing.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestAssessments(unittest.TestCase):
    """Core 4: assessment administration records (no scoring)."""

    def test_create_assessment_record(self):
        """Core 4 (AU-2): an administration record binds title, learner, course and state with an asm- id."""
        store, course = make_store()
        rec = store.create_assessment("Safety Quiz", "carol", INSTRUCTOR, course_id=course["id"])
        self.assertEqual(rec["id"], "asm-1")
        self.assertEqual(rec["state"], "scheduled")
        self.assertEqual(rec["responses"], [])

    def test_item_responses_stored_verbatim_no_score(self):
        """Core 4: item responses are stored as records verbatim; no score/grade field exists on the record (scoring is Extended; 0 claims in either tier of this category)."""
        store, course = make_store()
        rec = store.create_assessment("Safety Quiz", "carol", INSTRUCTOR, course_id=course["id"])
        updated = store.add_assessment_response(rec["id"], "q1", "b", INSTRUCTOR)
        self.assertEqual(updated["responses"], [{"item_id": "q1", "response": "b"}])
        self.assertNotIn("score", updated)
        self.assertNotIn("grade", updated)
        fetched = store.get_assessment(rec["id"], ADMIN)
        self.assertNotIn("score", fetched)

    def test_duplicate_item_response_rejected(self):
        """Core 4 (SI-10): a second response for the same item_id is a validation error."""
        store, course = make_store()
        rec = store.create_assessment("Quiz", "carol", INSTRUCTOR, course_id=course["id"])
        store.add_assessment_response(rec["id"], "q1", "b", INSTRUCTOR)
        with self.assertRaises(ValidationError):
            store.add_assessment_response(rec["id"], "q1", "c", INSTRUCTOR)

    def test_state_transitions_and_validation(self):
        """Core 4: administration state can be set to a known state; unknown state -> ValidationError; unknown course/session -> NotFoundError."""
        store, course = make_store()
        rec = store.create_assessment("Quiz", "carol", INSTRUCTOR, course_id=course["id"])
        moved = store.set_assessment_state(rec["id"], "administered", INSTRUCTOR)
        self.assertEqual(moved["state"], "administered")
        with self.assertRaises(ValidationError):
            store.set_assessment_state(rec["id"], "graded", INSTRUCTOR)
        with self.assertRaises(NotFoundError):
            store.create_assessment("Quiz", "carol", INSTRUCTOR, course_id="crs-999")
        with self.assertRaises(NotFoundError):
            store.create_assessment("Quiz", "carol", INSTRUCTOR, session_id="sch-999")

    def test_learner_scope_and_write_denied(self):
        """Core 4 / Core 9: learner may not create assessment records and reads only her own."""
        store, course = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_assessment("Quiz", "carol", LEARNER, course_id=course["id"])
        own = store.create_assessment("Quiz", "carol", INSTRUCTOR, course_id=course["id"])
        other = store.create_assessment("Quiz", "erin", INSTRUCTOR, course_id=course["id"])
        self.assertEqual(store.get_assessment(own["id"], LEARNER)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_assessment(other["id"], LEARNER)


if __name__ == "__main__":
    unittest.main()
