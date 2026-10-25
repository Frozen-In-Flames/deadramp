"""Evaluation record tests.

Traces to: Core function 5 (Evaluation records bound to applications;
rater entries stored verbatim; AU-2, AU-3, SI-10). Records only:
there is NO aggregate/average/score field anywhere (weighted
cumulative scoring is Extended), and these tests assert that.
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


def _setup():
    store, position, person = make_store()
    vacancy = store.create_vacancy(position["id"], "Analyst Opening", ADMIN)
    app = store.create_application("carol", vacancy["id"], SPECIALIST)
    return store, app


class TestEvaluations(unittest.TestCase):
    """Core 5: evaluation records and verbatim rater entries (no scoring)."""

    def test_create_evaluation_record(self):
        """Core 5 (AU-2): an evaluation binds application, kind and title with an evl- id, state scheduled and empty entries."""
        store, app = _setup()
        rec = store.create_evaluation(app["id"], "assessment", "Skills Assessment", SPECIALIST)
        self.assertEqual(rec["id"], "evl-1")
        self.assertEqual(rec["state"], "scheduled")
        self.assertEqual(rec["entries"], [])
        self.assertEqual(rec["kind"], "assessment")

    def test_entries_stored_verbatim_no_aggregate(self):
        """Core 5: rater entries are stored verbatim; no aggregate/average/score field exists on the record (weighted cumulative scoring is Extended)."""
        store, app = _setup()
        rec = store.create_evaluation(app["id"], "panel", "Panel Review", SPECIALIST)
        updated = store.add_evaluation_entry(rec["id"], "rater-1", 4, "Solid", SPECIALIST)
        updated = store.add_evaluation_entry(rec["id"], "rater-2", 5.5, "Strong", SPECIALIST)
        self.assertEqual(
            updated["entries"],
            [
                {"rater_ref": "rater-1", "rating": 4, "comment": "Solid"},
                {"rater_ref": "rater-2", "rating": 5.5, "comment": "Strong"},
            ],
        )
        for forbidden in ("score", "aggregate", "average", "total", "weighted_score"):
            self.assertNotIn(forbidden, updated)
        fetched = store.get_evaluation(rec["id"], ADMIN)
        self.assertNotIn("score", fetched)
        # Entries are deep-copied: mutating a fetched copy does not alter the record.
        fetched["entries"][0]["rating"] = 0
        self.assertEqual(store.get_evaluation(rec["id"], ADMIN)["entries"][0]["rating"], 4)

    def test_entry_validation(self):
        """Core 5 (SI-10): duplicate rater_ref, non-number rating, bool rating and non-string comment are validation errors."""
        store, app = _setup()
        rec = store.create_evaluation(app["id"], "assessment", "Quiz", SPECIALIST)
        store.add_evaluation_entry(rec["id"], "rater-1", 3, "Ok", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.add_evaluation_entry(rec["id"], "rater-1", 4, "Again", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.add_evaluation_entry(rec["id"], "rater-2", "high", "Text rating", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.add_evaluation_entry(rec["id"], "rater-2", True, "Bool rating", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.add_evaluation_entry(rec["id"], "rater-2", 4, 42, SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.add_evaluation_entry("evl-999", "rater-9", 4, "Ghost", SPECIALIST)

    def test_state_and_kind_validation(self):
        """Core 5: state moves scheduled -> completed; bad state/kind -> ValidationError; unknown application -> NotFoundError."""
        store, app = _setup()
        rec = store.create_evaluation(app["id"], "assessment", "Quiz", SPECIALIST)
        self.assertEqual(store.set_evaluation_state(rec["id"], "completed", SPECIALIST)["state"], "completed")
        with self.assertRaises(ValidationError):
            store.set_evaluation_state(rec["id"], "scored", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.create_evaluation(app["id"], "exam", "X", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.create_evaluation("app-999", "assessment", "X", SPECIALIST)

    def test_employee_scope_through_application(self):
        """Core 5 / Core 11: an employee reads evaluations only through her own applications, and may not write evaluations."""
        store, app = _setup()
        store.create_person("erin", ADMIN, kind="applicant")
        # second application for erin on a new vacancy
        positions = store.list_positions(ADMIN)
        vac2 = store.create_vacancy(positions[0]["id"], "Second Opening", ADMIN)
        other_app = store.create_application("erin", vac2["id"], SPECIALIST)
        with self.assertRaises(PermissionDenied):
            store.create_evaluation(app["id"], "assessment", "X", EMPLOYEE)
        own = store.create_evaluation(app["id"], "assessment", "Mine", SPECIALIST)
        other = store.create_evaluation(other_app["id"], "assessment", "Theirs", SPECIALIST)
        self.assertEqual(store.get_evaluation(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_evaluation(other["id"], EMPLOYEE)
        self.assertEqual([e["id"] for e in store.list_evaluations(EMPLOYEE)], [own["id"]])
        self.assertEqual(len(store.list_evaluations(ADMIN, application_id=app["id"])), 1)


if __name__ == "__main__":
    unittest.main()
