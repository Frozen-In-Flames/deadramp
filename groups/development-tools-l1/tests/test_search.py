"""Search tests.

Traces to: Core function 8 (search, AC-3) -- case-insensitive substring
over names/titles/versions; requires the ``search`` action.
"""

import unittest

from devtools.access import User
from devtools_helpers import ADMIN, VIEWER, make_store
from devtools.errors import PermissionDenied, ValidationError


class TestSearch(unittest.TestCase):
    """Core 8: search across projects/issues/reviews/releases/artifacts."""

    def _seed(self):
        store, project = make_store()
        store.create_issue(project["id"], "Widget crash", ADMIN)
        store.create_review(project["id"], "Widget review", ADMIN)
        store.create_release(project["id"], "widget-1.0", ADMIN)
        store.register_artifact(project["id"], "widget-pkg", ADMIN, content="x")
        store.create_project("Other Thing", ADMIN)
        return store, project

    def test_search_hits_all_families_case_insensitive(self):
        """Core 8: 'WIDGET' hits project, issue, review, release version, and artifact name."""
        store, _ = self._seed()
        result = store.search("WIDGET", ADMIN)
        self.assertEqual(set(result), {"projects", "issues", "reviews", "releases", "artifacts"})
        self.assertEqual(len(result["projects"]), 1)
        self.assertEqual(len(result["issues"]), 1)
        self.assertEqual(len(result["reviews"]), 1)
        self.assertEqual(len(result["releases"]), 1)
        self.assertEqual(len(result["artifacts"]), 1)

    def test_search_no_hit_empty_lists(self):
        """Core 8: a non-matching query returns empty lists, not an error."""
        store, _ = self._seed()
        result = store.search("nonexistent-term", VIEWER)
        self.assertTrue(all(v == [] for v in result.values()))

    def test_empty_query_validation(self):
        """Core 8 (SI-10): empty query -> ValidationError."""
        store, _ = self._seed()
        with self.assertRaises(ValidationError):
            store.search("", ADMIN)
        with self.assertRaises(ValidationError):
            store.search("   ", ADMIN)

    def test_search_requires_search_action(self):
        """Core 8/9 (AC-3): a User whose role lacks search is denied; viewer (has search) is allowed."""
        store, _ = self._seed()
        stranger = User("mallory", "superuser")
        with self.assertRaises(PermissionDenied):
            store.search("widget", stranger)
        self.assertEqual(len(store.search("widget", VIEWER)["projects"]), 1)


if __name__ == "__main__":
    unittest.main()
