"""Performance review tests.

Traces to: Core function 7 (Performance review records per person +
cycle with ISO period dates and a recorded outcome label; AU-6,
SI-12).
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestPerformance(unittest.TestCase):
    """Core 7: performance review records."""

    def test_create_review_record(self):
        """Core 7: a review binds person_ref, cycle and ISO period dates with a rev- id, state planned and outcome None."""
        store, _, _ = make_store()
        rec = store.create_performance_review(
            "carol", "2026-annual", SPECIALIST,
            period_start="2026-01-01", period_end="2026-12-31",
        )
        self.assertEqual(rec["id"], "rev-1")
        self.assertEqual(rec["state"], "planned")
        self.assertIsNone(rec["outcome"])
        self.assertEqual(rec["cycle"], "2026-annual")

    def test_set_review_state_with_outcome(self):
        """Core 7 (AU-2): set_review_state records the state and an optional outcome label string."""
        store, _, _ = make_store()
        rec = store.create_performance_review("carol", "2026-annual", SPECIALIST)
        moved = store.set_review_state(rec["id"], "in_progress", SPECIALIST)
        self.assertEqual(moved["state"], "in_progress")
        self.assertIsNone(moved["outcome"])
        done = store.set_review_state(rec["id"], "completed", SPECIALIST, outcome="meets")
        self.assertEqual(done["state"], "completed")
        self.assertEqual(done["outcome"], "meets")
        with self.assertRaises(ValidationError):
            store.set_review_state(rec["id"], "rated", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.set_review_state(rec["id"], "completed", SPECIALIST, outcome=5)
        with self.assertRaises(NotFoundError):
            store.set_review_state("rev-999", "completed", SPECIALIST)

    def test_date_validation_and_unknown_person(self):
        """Core 7 (SI-10): non-ISO dates and end before start are validation errors; unknown person -> NotFoundError; no id consumed."""
        store, _, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_performance_review("carol", "2026", SPECIALIST, period_start="Jan 2026")
        with self.assertRaises(ValidationError):
            store.create_performance_review(
                "carol", "2026", SPECIALIST, period_start="2026-12-31", period_end="2026-01-01"
            )
        with self.assertRaises(NotFoundError):
            store.create_performance_review("ghost", "2026", SPECIALIST)
        rec = store.create_performance_review("carol", "2026", SPECIALIST)
        self.assertEqual(rec["id"], "rev-1")

    def test_employee_scope_and_write_denied(self):
        """Core 7 / Core 11: an employee may not create reviews and reads only her own."""
        store, _, _ = make_store()
        store.create_person("erin", ADMIN, kind="employee")
        with self.assertRaises(PermissionDenied):
            store.create_performance_review("carol", "2026", EMPLOYEE)
        own = store.create_performance_review("carol", "2026", SPECIALIST)
        other = store.create_performance_review("erin", "2026", SPECIALIST)
        self.assertEqual(store.get_performance_review(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_performance_review(other["id"], EMPLOYEE)
        self.assertEqual([r["id"] for r in store.list_performance_reviews(EMPLOYEE)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
