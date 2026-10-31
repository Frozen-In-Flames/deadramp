"""Personnel case tests.

Traces to: Core function 9 (Personnel cases -- personnel actions,
awards, labor-relations and general cases per person; AU-2, SI-12).
"""

import unittest

from hr_helpers import ADMIN, EMPLOYEE, SPECIALIST, make_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestCases(unittest.TestCase):
    """Core 9: personnel case records per person."""

    def test_create_case_record(self):
        """Core 9: a case binds person_ref, kind and title with a cas- id and state opened."""
        store, _, _ = make_store()
        rec = store.create_case("carol", "award", "Service Award", SPECIALIST)
        self.assertEqual(rec["id"], "cas-1")
        self.assertEqual(rec["state"], "opened")
        self.assertEqual(rec["kind"], "award")
        for kind in ("personnel_action", "labor_relations", "general"):
            made = store.create_case("carol", kind, "Case %s" % kind, SPECIALIST)
            self.assertEqual(made["kind"], kind)

    def test_set_case_state(self):
        """Core 9: state moves opened -> in_review -> closed; bad state -> ValidationError; unknown id -> NotFoundError."""
        store, _, _ = make_store()
        rec = store.create_case("carol", "general", "Inquiry", SPECIALIST)
        self.assertEqual(store.set_case_state(rec["id"], "in_review", SPECIALIST)["state"], "in_review")
        self.assertEqual(store.set_case_state(rec["id"], "closed", ADMIN)["state"], "closed")
        with self.assertRaises(ValidationError):
            store.set_case_state(rec["id"], "archived", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.set_case_state("cas-999", "closed", SPECIALIST)

    def test_validation_and_unknown_person(self):
        """Core 9 (SI-10): bad kind / empty title rejected; unknown person -> NotFoundError; no id consumed."""
        store, _, _ = make_store()
        with self.assertRaises(ValidationError):
            store.create_case("carol", "discipline", "X", SPECIALIST)
        with self.assertRaises(ValidationError):
            store.create_case("carol", "general", "", SPECIALIST)
        with self.assertRaises(NotFoundError):
            store.create_case("ghost", "general", "X", SPECIALIST)
        rec = store.create_case("carol", "general", "X", SPECIALIST)
        self.assertEqual(rec["id"], "cas-1")

    def test_employee_scope_and_write_denied(self):
        """Core 9 / Core 11: an employee may not create cases and reads only her own."""
        store, _, _ = make_store()
        store.create_person("erin", ADMIN, kind="employee")
        with self.assertRaises(PermissionDenied):
            store.create_case("carol", "general", "X", EMPLOYEE)
        own = store.create_case("carol", "general", "Mine", SPECIALIST)
        other = store.create_case("erin", "general", "Theirs", SPECIALIST)
        self.assertEqual(store.get_case(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_case(other["id"], EMPLOYEE)
        self.assertEqual([c["id"] for c in store.list_cases(EMPLOYEE)], [own["id"]])


if __name__ == "__main__":
    unittest.main()
