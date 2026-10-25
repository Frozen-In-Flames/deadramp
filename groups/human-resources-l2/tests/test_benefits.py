"""Benefits record tests.

Traces to: Core function 8 (Benefits records -- benefit enrollments
and retirement cases per person, keyed by an opaque plan_ref; AU-2,
SI-12).
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestBenefits(unittest.TestCase):
    """Core 8: benefits records per person."""

    def test_create_benefits_record(self):
        """Core 8: a benefits record binds person_ref, kind and plan_ref with a ben- id and state pending."""
        store, _, _ = make_store()
        rec = store.create_benefits_record("carol", "benefit_enrollment", "plan-a", SPECIALIST)
        self.assertEqual(rec["id"], "ben-1")
        self.assertEqual(rec["state"], "pending")
        self.assertEqual(rec["kind"], "benefit_enrollment")
        rec2 = store.create_benefits_record("carol", "retirement_case", "ret-1", SPECIALIST)
        self.assertEqual(rec2["kind"], "retirement_case")

    def test_set_benefits_state(self):
        """Core 8: state moves pending -> active -> closed; bad state -> ValidationError; unknown id -> NotFoundError."""
        store, _, _ = make_store()
        rec = store.create_benefits_record("carol", "benefit_enrollment", "plan-a", SPECIALIST)
        self.assertEqual(store.set_benefits_state(rec["id"], "active", SPECIALIST)["state"], "active")
        self.assertEqual(store.set_benefits_state(rec["id"], "closed", ADMIN)["state"], "closed")
        with self.assertRaises(ValidationError):
            store.set_benefits_state(rec["id"], "paid", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.set_benefits_state("ben-999", "active", SPECIALIST)

    def test_validation_and_unknown_person(self):
        """Core 8 (SI-10): bad kind / empty plan_ref rejected; unknown person -> NotFoundError; no id consumed."""
        store, _, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_benefits_record("carol", "pension", "plan-a", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.create_benefits_record("carol", "benefit_enrollment", "", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.create_benefits_record("ghost", "benefit_enrollment", "plan-a", SPECIALIST)
        rec = store.create_benefits_record("carol", "benefit_enrollment", "plan-a", SPECIALIST)
        self.assertEqual(rec["id"], "ben-1")

    def test_employee_scope_and_write_denied(self):
        """Core 8 / Core 11: an employee may not create benefits records and reads only her own."""
        store, _, _ = make_store()
        store.create_person("erin", ADMIN, kind="employee")
        with self.assertRaises(PermissionDenied):
            store.create_benefits_record("carol", "benefit_enrollment", "p", EMPLOYEE)
        own = store.create_benefits_record("carol", "benefit_enrollment", "p", SPECIALIST)
        other = store.create_benefits_record("erin", "benefit_enrollment", "p", SPECIALIST)
        self.assertEqual(store.get_benefits_record(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_benefits_record(other["id"], EMPLOYEE)
        self.assertEqual([r["id"] for r in store.list_benefits_records(EMPLOYEE)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
