"""Course/catalog registry tests.

Traces to: Core function 1 (Course/catalog & training program
registry; claim family course_catalog 3/8; CM-6, SI-12).
"""

import unittest

from learn_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, fresh_store
from learn.errors import NotFoundError, PermissionDenied, ValidationError


class TestCourses(unittest.TestCase):
    """Core 1: course/catalog registry records."""

    def test_create_course_shape_and_ids(self):
        """Core 1 (CM-6): creation returns a crs- record with provenance; ids are sequential."""
        store = fresh_store()
        first = store.create_course("Safety Basics", ADMIN, code="SAFE-101")
        second = store.create_course("Safety Program", ADMIN, kind="program")
        self.assertEqual(first["id"], "crs-1")
        self.assertEqual(second["id"], "crs-2")
        self.assertEqual(first["kind"], "course")
        self.assertEqual(second["kind"], "program")
        self.assertEqual(first["created_by"], "alice")
        self.assertIn("created_utc", first)

    def test_get_and_list_sorted(self):
        """Core 1: get returns the record; list is sorted by id; all roles may read."""
        store = fresh_store()
        store.create_course("B Course", ADMIN)
        store.create_course("A Course", ADMIN)
        self.assertEqual([c["id"] for c in store.list_courses(LEARNER)], ["crs-1", "crs-2"])
        self.assertEqual(store.get_course("crs-1", AUDITOR)["title"], "B Course")

    def test_validation(self):
        """Core 1 (SI-10): empty title / bad kind rejected; failed creates consume no id."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_course("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_course("X", ADMIN, kind="module")
        course = store.create_course("Ok", ADMIN)
        self.assertEqual(course["id"], "crs-1")

    def test_catalog_write_admin_only(self):
        """Core 1 / Core 9 (AC-3): instructor, learner and auditor may not create registry entries."""
        store = fresh_store()
        for actor in (INSTRUCTOR, LEARNER, AUDITOR):
            with self.assertRaises(PermissionDenied):
                store.create_course("Nope", actor)
        self.assertEqual(store.list_courses(ADMIN), [])

    def test_unknown_course_not_found(self):
        """Core 1: unknown course id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_course("crs-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
