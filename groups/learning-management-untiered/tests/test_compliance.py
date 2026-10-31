"""Compliance assignment & derived-status tests.

Traces to: Core function 9 (Compliance assignments with due dates +
derived current/overdue/completed status). The stored record
(``asg-``) carries NO "status" key: status is derived at read time --
"completed" if a completed progress record exists for
learner_ref+course, else "overdue" if the as_of date is after the due
date, else "current". Derivation is deterministic in as_of.
compliance_write is admin-only; learner scope applies (Core 12).
"""

import unittest

from lms_helpers import ADMIN, INSTRUCTOR, LEARNER, make_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError

AS_OF = "2026-06-15"


class TestCompliance(unittest.TestCase):
    """Core 9: compliance assignments and deterministic status derivation."""

    def _setup(self):
        store, learner, course = make_store()
        assignment = store.create_compliance_assignment("carol", course["id"],
                                                        "2026-06-01", ADMIN)
        return store, course, assignment

    def test_assignment_record_has_no_stored_status(self):
        """Core 9: the record returned at creation carries due date but NO 'status' key -- status exists only as a derived read-time view."""
        _, _, assignment = self._setup()
        self.assertEqual(assignment["id"], "asg-1")
        self.assertEqual(assignment["learner_ref"], "carol")
        self.assertEqual(assignment["due_date"], "2026-06-01")
        self.assertNotIn("status", assignment)

    def test_overdue_when_past_due_and_incomplete(self):
        """Core 9: as_of after due date with no completion record -> overdue, in both the get view and the compliance_status summary."""
        store, _, assignment = self._setup()
        view = store.get_compliance_assignment(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(view["status"], "overdue")
        self.assertFalse(view["completed"])
        self.assertEqual(view["as_of"], AS_OF)
        summary = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(summary["status"], "overdue")
        self.assertFalse(summary["completed"])
        self.assertEqual(summary["as_of"], AS_OF)
        self.assertEqual(summary["due_date"], "2026-06-01")
        self.assertEqual(summary["learner_ref"], "carol")
        self.assertIn(summary.get("assignment_id") or summary.get("id"),
                      (assignment["id"],))

    def test_current_on_or_before_due_date(self):
        """Core 9: as_of on the due date itself -> current (overdue is strictly after)."""
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
        """Core 9: a completed progress record for learner_ref+course makes the derived status completed even past the due date."""
        store, course, assignment = self._setup()
        store.record_progress("carol", course["id"], "completed", INSTRUCTOR)
        summary = store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)
        self.assertEqual(summary["status"], "completed")
        self.assertTrue(summary["completed"])
        # A completion for a DIFFERENT course does not complete it.
        other = store.create_course("Other Course", ADMIN)
        second = store.create_compliance_assignment("carol", other["id"],
                                                    "2026-06-01", ADMIN)
        self.assertEqual(
            store.compliance_status(second["id"], ADMIN, as_of=AS_OF)["status"],
            "overdue",
        )

    def test_in_progress_does_not_complete(self):
        """Core 9: an in_progress record does not satisfy the assignment -- still overdue past due."""
        store, course, assignment = self._setup()
        store.record_progress("carol", course["id"], "in_progress", INSTRUCTOR)
        self.assertEqual(
            store.compliance_status(assignment["id"], ADMIN, as_of=AS_OF)["status"],
            "overdue",
        )

    def test_derivation_deterministic_in_as_of(self):
        """Core 9: the same assignment reads current, overdue, current again purely as a function of the explicit as_of parameter."""
        store, _, assignment = self._setup()
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-05-01")["status"], "current")
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-07-01")["status"], "overdue")
        self.assertEqual(store.compliance_status(assignment["id"], ADMIN, as_of="2026-05-01")["status"], "current")

    def test_list_compliance_derives_each(self):
        """Core 9: list_compliance returns every assignment with its derived status at as_of, and filters by learner_ref."""
        store, course, assignment = self._setup()
        store.create_learner("erin", "Erin Learner", ADMIN)
        second = store.create_compliance_assignment("erin", course["id"],
                                                    "2026-12-01", ADMIN)
        views = store.list_compliance(ADMIN, as_of=AS_OF)
        by_id = {v["id"]: v["status"] for v in views}
        self.assertEqual(by_id[assignment["id"]], "overdue")
        self.assertEqual(by_id[second["id"]], "current")
        self.assertEqual(
            [v["id"] for v in store.list_compliance(ADMIN, as_of=AS_OF,
                                                    learner_ref="erin")],
            [second["id"]],
        )

    def test_validation_and_permissions(self):
        """Core 9 / Core 12: bad due date -> ValidationError; unknown course -> NotFoundError; compliance_write is admin-only (instructor denied); learner scope applies to reads."""
        store, _, course = make_store()
        with self.assertRaises(ValidationError):
            store.create_compliance_assignment("carol", course["id"], "June 1", ADMIN)
        with self.assertRaises(NotFoundError):
            store.create_compliance_assignment("carol", "crs-999", "2026-06-01", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.create_compliance_assignment("carol", course["id"], "2026-06-01",
                                               INSTRUCTOR)
        with self.assertRaises(PermissionDenied):
            store.create_compliance_assignment("carol", course["id"], "2026-06-01",
                                               LEARNER)
        assignment = store.create_compliance_assignment("carol", course["id"],
                                                        "2026-06-01", ADMIN)
        self.assertEqual(assignment["id"], "asg-1")
        self.assertEqual(
            store.compliance_status(assignment["id"], LEARNER, as_of=AS_OF)["status"],
            "overdue",
        )
        store.create_learner("erin", "Erin Learner", ADMIN)
        other = store.create_compliance_assignment("erin", course["id"],
                                                   "2026-06-01", ADMIN)
        with self.assertRaises(PermissionDenied):
            store.compliance_status(other["id"], LEARNER, as_of=AS_OF)
        with self.assertRaises(NotFoundError):
            store.compliance_status("asg-999", ADMIN, as_of=AS_OF)


if __name__ == "__main__":
    unittest.main()
