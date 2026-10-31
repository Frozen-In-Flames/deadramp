"""Code-review records tests.

Traces to: Core function 3 (code-review records, AU-2) -- ``rev-``
records only; no merge engine.
"""

import unittest

from devtools_helpers import ADMIN, make_store
from devtools.errors import NotFoundError, ValidationError


class TestReviews(unittest.TestCase):
    """Core 3: review creation, listing, and state transitions."""

    def test_create_shape(self):
        """Core 3: create_review returns rev-N with state open."""
        store, project = make_store()
        rev = store.create_review(project["id"], "Review PR 1", ADMIN, source_ref="branch-x")
        self.assertEqual(rev["id"], "rev-1")
        self.assertEqual(rev["state"], "open")
        self.assertEqual(rev["source_ref"], "branch-x")

    def test_unknown_project(self):
        """Core 3: review for unknown project -> NotFoundError."""
        store, _ = make_store()
        with self.assertRaises(NotFoundError):
            store.create_review("prj-999", "X", ADMIN)

    def test_transitions_happy(self):
        """Core 3 state gate: open->changes_requested->open->approved->merged."""
        store, project = make_store()
        rev = store.create_review(project["id"], "R", ADMIN)
        for target in ("changes_requested", "open", "approved", "merged"):
            rev = store.set_review_state(rev["id"], target, ADMIN)
            self.assertEqual(rev["state"], target)

    def test_terminal_and_illegal_rejected(self):
        """Core 3 state gate: merged/closed are terminal; illegal transitions -> ValidationError, unchanged."""
        store, project = make_store()
        rev = store.create_review(project["id"], "R", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_review_state(rev["id"], "merged", ADMIN)
        self.assertEqual(store.get_review(rev["id"])["state"], "open")
        store.set_review_state(rev["id"], "approved", ADMIN)
        store.set_review_state(rev["id"], "merged", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_review_state(rev["id"], "open", ADMIN)
        rev2 = store.create_review(project["id"], "R2", ADMIN)
        store.set_review_state(rev2["id"], "closed", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_review_state(rev2["id"], "open", ADMIN)

    def test_list_filter(self):
        """Core 3: list_reviews filters by project_id."""
        store, project = make_store()
        store.create_review(project["id"], "A", ADMIN)
        self.assertEqual(len(store.list_reviews(project_id=project["id"])), 1)
        self.assertEqual(store.list_reviews(project_id="prj-999"), [])


if __name__ == "__main__":
    unittest.main()
