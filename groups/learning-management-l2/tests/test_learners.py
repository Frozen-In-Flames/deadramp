"""Learner registry tests.

Traces to: Core function 1 (Learner registry) -- create_learner /
get_learner / list_learners in ``lms/store.py``; ids are ``lrn-``
sequential; a duplicate ref is a ValidationError; learner_write is
admin-only (Core function 12).
"""

import unittest

from lms_helpers import ADMIN, AUDITOR, INSTRUCTOR, LEARNER, fresh_store
from lms.errors import NotFoundError, PermissionDenied, ValidationError


class TestLearners(unittest.TestCase):
    """Core 1: learner registry records."""

    def test_create_learner_shape_and_ids(self):
        """Core 1: creation returns an lrn- record carrying ref/label with provenance; ids are sequential."""
        store = fresh_store()
        first = store.create_learner("carol", "Carol Learner", ADMIN)
        second = store.create_learner("erin", "Erin Learner", ADMIN)
        self.assertEqual(first["id"], "lrn-1")
        self.assertEqual(second["id"], "lrn-2")
        self.assertEqual(first["ref"], "carol")
        self.assertEqual(first["label"], "Carol Learner")
        self.assertEqual(first["created_by"], "alice")
        self.assertIn("created_utc", first)

    def test_duplicate_ref_rejected_no_id_consumed(self):
        """Core 1: a duplicate learner ref -> ValidationError, changes nothing, and consumes no id."""
        store = fresh_store()
        store.create_learner("carol", "Carol Learner", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_learner("carol", "Carol Again", ADMIN)
        self.assertEqual(len(store.list_learners(ADMIN)), 1)
        nxt = store.create_learner("erin", "Erin Learner", ADMIN)
        self.assertEqual(nxt["id"], "lrn-2")

    def test_validation_empty_ref_or_label(self):
        """Core 1: empty/blank ref or label -> ValidationError; failed creates consume no id."""
        store = fresh_store()
        for ref, label in (("", "X"), ("  ", "X"), ("carol", ""), ("carol", "  ")):
            with self.subTest(ref=ref, label=label):
                with self.assertRaises(ValidationError):
                    store.create_learner(ref, label, ADMIN)
        learner = store.create_learner("carol", "Carol Learner", ADMIN)
        self.assertEqual(learner["id"], "lrn-1")

    def test_learner_write_admin_only(self):
        """Core 1 / Core 12: learner_write is admin-only -- instructor, learner and auditor may not create learners."""
        store = fresh_store()
        for actor in (INSTRUCTOR, LEARNER, AUDITOR):
            with self.subTest(actor=actor.name):
                with self.assertRaises(PermissionDenied):
                    store.create_learner("carol", "Carol Learner", actor)
        self.assertEqual(store.list_learners(ADMIN), [])

    def test_get_and_list(self):
        """Core 1: get returns the record; list returns all learners sorted by id; staff roles may read."""
        store = fresh_store()
        store.create_learner("erin", "Erin Learner", ADMIN)
        carol = store.create_learner("carol", "Carol Learner", ADMIN)
        self.assertEqual(store.get_learner(carol["id"], AUDITOR)["ref"], "carol")
        self.assertEqual(store.get_learner(carol["id"])["label"], "Carol Learner")
        self.assertEqual(
            [lrn["id"] for lrn in store.list_learners(INSTRUCTOR)], ["lrn-1", "lrn-2"]
        )

    def test_unknown_learner_not_found(self):
        """Core 1: unknown learner id -> NotFoundError."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.get_learner("lrn-999", ADMIN)


if __name__ == "__main__":
    unittest.main()
