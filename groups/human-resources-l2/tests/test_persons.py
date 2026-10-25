"""Person record tests.

Traces to: Core function 1 (Person records; privacy discipline --
opaque person_ref only, exact record shape; AC-2, AU-2, SI-12).
"""

import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, fresh_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestPersons(unittest.TestCase):
    """Core 1: person records (exact shape, opaque person_ref only)."""

    def test_create_person_shape_and_ids(self):
        """Core 1: creation returns exactly {id, person_ref, kind, status, created_by, created_utc} with a per- id; applicant kind starts applicant, employee kind starts active."""
        store = fresh_store()
        first = store.create_person("carol", ADMIN, kind="employee")
        second = store.create_person("erin", ADMIN)
        self.assertEqual(
            set(first), {"id", "person_ref", "kind", "status", "created_by", "created_utc"}
        )
        self.assertEqual(first["id"], "per-1")
        self.assertEqual(second["id"], "per-2")
        self.assertEqual(first["status"], "active")
        self.assertEqual(second["status"], "applicant")
        self.assertEqual(second["kind"], "applicant")
        self.assertEqual(first["created_by"], "alice")

    def test_duplicate_person_ref_rejected_no_id_consumed(self):
        """Core 1 (SI-10): a duplicate person_ref is a validation error and consumes no id."""
        store = fresh_store()
        store.create_person("carol", ADMIN, kind="employee")
        with self.assertRaises(ValidationError):
            store.create_person("carol", SPECIALIST)
        nxt = store.create_person("erin", ADMIN)
        self.assertEqual(nxt["id"], "per-2")

    def test_set_person_status(self):
        """Core 1: status moves applicant -> active -> separated; bad status -> ValidationError; unknown id -> NotFoundError."""
        store = fresh_store()
        person = store.create_person("erin", ADMIN)
        moved = store.set_person_status(person["id"], "active", SPECIALIST)
        self.assertEqual(moved["status"], "active")
        moved = store.set_person_status(person["id"], "separated", ADMIN)
        self.assertEqual(moved["status"], "separated")
        with self.assertRaises(ValidationError):
            store.set_person_status(person["id"], "terminated", ADMIN)
        with self.assertRaises(NotFoundError):
            store.set_person_status("per-999", "active", ADMIN)

    def test_validation_and_write_roles(self):
        """Core 1 / Core 11 (AC-3): empty person_ref / bad kind rejected; employee and auditor may not write persons."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_person("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_person("x", ADMIN, kind="contractor")
        for actor in (EMPLOYEE, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_person("x", actor)
        self.assertEqual(store.list_persons(ADMIN), [])

    def test_employee_scope_reads(self):
        """Core 1 / Core 11: an employee reads her own person record only, is denied another's, and lists only her own."""
        store = fresh_store()
        own = store.create_person("carol", ADMIN, kind="employee")
        other = store.create_person("erin", ADMIN, kind="employee")
        self.assertEqual(store.get_person(own["id"], EMPLOYEE)["id"], own["id"])
        with self.assertRaises(PermissionDenied):
            store.get_person(other["id"], EMPLOYEE)
        self.assertEqual([p["id"] for p in store.list_persons(EMPLOYEE)], [own["id"]])
        self.assertEqual(len(store.list_persons(AUDITOR)), 2)

    def test_unknown_person_not_found(self):
        """Core 1: unknown person id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_person("per-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
