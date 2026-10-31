"""Position record tests.

Traces to: Core function 2 (Position classification records --
series/grade are classification attributes, NOT pay data; no
compensation field exists; CM-6, SI-12).
"""

import unittest

from hr_helpers import ADMIN, AUDITOR, EMPLOYEE, SPECIALIST, fresh_store
from hr.errors import NotFoundError, PermissionDenied, ValidationError


class TestPositions(unittest.TestCase):
    """Core 2: position classification records."""

    def test_create_position_shape_and_ids(self):
        """Core 2 (CM-6): creation returns a pos- record with classification attributes and status vacant; ids are sequential."""
        store = fresh_store()
        first = store.create_position("Program Analyst", ADMIN, series="0343", grade="13", organization="Ops")
        second = store.create_position("Clerk", SPECIALIST)
        self.assertEqual(first["id"], "pos-1")
        self.assertEqual(second["id"], "pos-2")
        self.assertEqual(first["series"], "0343")
        self.assertEqual(first["grade"], "13")
        self.assertEqual(first["status"], "vacant")
        self.assertEqual(first["created_by"], "alice")
        self.assertNotIn("salary", first)
        self.assertNotIn("compensation", first)

    def test_get_and_list_sorted(self):
        """Core 2: get returns the record; list is sorted by id; all roles may read (positions are not person-scoped)."""
        store = fresh_store()
        store.create_position("B Position", ADMIN)
        store.create_position("A Position", ADMIN)
        self.assertEqual([p["id"] for p in store.list_positions(EMPLOYEE)], ["pos-1", "pos-2"])
        self.assertEqual(store.get_position("pos-1", AUDITOR)["title"], "B Position")

    def test_set_position_status(self):
        """Core 2: status moves vacant -> filled -> abolished; bad status -> ValidationError; unknown id -> NotFoundError."""
        store = fresh_store()
        pos = store.create_position("Analyst", ADMIN)
        self.assertEqual(store.set_position_status(pos["id"], "filled", SPECIALIST)["status"], "filled")
        self.assertEqual(store.set_position_status(pos["id"], "abolished", ADMIN)["status"], "abolished")
        with self.assertRaises(ValidationError):
            store.set_position_status(pos["id"], "open", ADMIN)
        with self.assertRaises(NotFoundError):
            store.set_position_status("pos-999", "filled", ADMIN)

    def test_validation(self):
        """Core 2 (SI-10): empty title rejected; failed creates consume no id."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_position("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_position("X", ADMIN, series=343)
        pos = store.create_position("Ok", ADMIN)
        self.assertEqual(pos["id"], "pos-1")

    def test_position_write_roles(self):
        """Core 2 / Core 11 (AC-3): employee and auditor may not create positions."""
        store = fresh_store()
        for actor in (EMPLOYEE, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_position("Nope", actor)
        self.assertEqual(store.list_positions(ADMIN), [])

    def test_unknown_position_not_found(self):
        """Core 2: unknown position id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_position("pos-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
