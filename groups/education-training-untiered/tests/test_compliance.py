"""Compliance assignment & derived-status tests.

Traces to: Core function 6 (Compliance assignments with due dates +
derived current/overdue status; claim family compliance_training
2/8; AU-6, CA-7, CM-6). Status is derived at read time from due date
vs. completion record against an explicit ``as_of`` reference date --
never stored, never wall-clock dependent in these tests.
"""

import unittest

from learn_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError

AS_OF = "2026-06-15"


class TestCompliance(unittest.TestCase):
    """Core 6: compliance assignments and deterministic status derivation."""

    def _setup(self):
        store, course = make_store()
        assignment = store.create_compliance_assignment("carol", course["id"], "2026-06-01", ADMIN)
        return store, course, assignment

    def test_assignment_record_has_no_stored_status(self):
        """Core 6 (CA-7): the stored assignment record carries due date but NO status field -- status exists only as a derived read-time view."""
        _, _, assignment = self._setup()
        self.assertEqual(assignment["id"], "cmp-1")
        self.assertEqual(assignment["due_date"], "2026-06-01")
        self.assertNotIn("status", assignment)

    def test_overdue_when_past_due_and_incomplete(self):
        """Core 6: as_of after due date with no completion record -> overdue."""
        store, _, assignment = self._setup()
        view = store.get_compliance_assignment(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(view["status"], "overdue")
        self.assertFalse(view["completed"])
        summary = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(summary["status"], "overdue")
        self.assertEqual(summary["as_of"], AS_OF)

    def test_current_on_or_before_due_date(self):
        """Core 6: as_of on the due date itself -> current (overdue is strictly after)."""
        store, _, assignment = self._setup()
        self.assertEqual(
            store.compliance_status(assignment["id"], ADMIN, as_of="2026-06-01")["status"],
            "current",
        )
        self.assertEqual(
            store.compliance_status(assignment["id"], ADMIN, as_of="2026-05-01")["status"],
            "current",
        )

    def test_completed_progress_overrides_overdue(self):
        """Core 6: a completed progress record for learner+course makes the derived status completed even past the due date."""
        store, course, assignment = self._setup()
        store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        summary = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["completed"])

    def test_in_progress_does_not_complete(self):
        """Core 6: an in_progress record does not satisfy the assignment -- still overdue past due."""
        store, course, assignment = self._setup()
        store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR)
        self.assertEqual(
            store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"], "overdue"
        )

    def test_derivation_deterministic_in_as_of(self):
        """Core 6: the same assignment reads current, overdue, current again purely as a function of the explicit as_of parameter."""
        store, _, assignment = self._setup()
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-05-01")["status"], "current")
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-07-01")["status"], "overdue")
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-05-01")["status"], "current")

    def test_list_compliance_derives_each(self):
        """Core 6: list_compliance returns every assignment with its derived status at as_of."""
        store, course, assignment = self._setup()
        second = store.create_compliance_assignment("erin", course["id"], "2026-12-01", ADMIN)
        views = store.list_compliance(ADMIN, as_of=AS_OF)
        by_id = {v["id"]: v["status"] for v in views}
        self.assertEqual(by_id[assignment["id"]], "overdue")
        self.assertEqual(by_id[second["id"]], "current")

    def test_validation_and_permissions(self):
        """Core 6 (SI-10/AC-3): bad due date -> ValidationError; unknown course -> NotFoundError; compliance_write is admin-only; learner scope applies to reads."""
        store, course = make_store()
        with self.assertRaises(ValidationError):
            store.create_compliance_assignment("carol", course["id"], "June 1", ADMIN)
        with self.assertRaises(NotFoundError):
            store.create_compliance_assignment("carol", "crs-999", "2026-06-01", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_compliance_assignment("carol", course["id"], "2026-06-01", INSTRUCTOR)
        assignment = store.create_compliance_assignment("carol", course["id"], "2026-06-01", ADMIN)
        self.assertEqual(
            store.compliance_status(assignment["id"], LEARNER, as_of=AS_OF)["status"], "overdue"
        )
        other = store.create_compliance_assignment("erin", course["id"], "2026-06-01", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.compliance_status(other["id"], LEARNER, as_of=AS_OF)


if __name__ == "__main__":
    unittest.main()
