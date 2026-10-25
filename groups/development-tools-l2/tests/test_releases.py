"""Release records tests.

Traces to: Core function 5 (release records, AU-2/SI-10) -- ``rel-``
records; duplicate version within a project rejected.
"""

import unittest

from devtools_helpers import ADMIN, fresh_store, make_store
from devtools.errors import NotFoundError, ValidationError


class TestReleases(unittest.TestCase):
    """Core 5: release creation and per-project version uniqueness."""

    def test_create_shape(self):
        """Core 5: create_release returns rel-N with version/notes/build_id."""
        store, project = make_store()
        b = store.record_build(project["id"], ADMIN)
        rel = store.create_release(project["id"], "v1.0.0", ADMIN, notes="first", build_id=b["id"])
        self.assertEqual(rel["id"], "rel-1")
        self.assertEqual(rel["version"], "v1.0.0")
        self.assertEqual(rel["build_id"], b["id"])

    def test_duplicate_version_same_project_rejected(self):
        """Core 5 (SI-10): duplicate version in same project -> ValidationError, no id consumed."""
        store, project = make_store()
        store.create_release(project["id"], "v1", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_release(project["id"], "v1", ADMIN)
        self.assertEqual(store.create_release(project["id"], "v2", ADMIN)["id"], "rel-2")

    def test_same_version_different_project_ok(self):
        """Core 5: same version in a different project is fine."""
        store = fresh_store()
        p1 = store.create_project("One", ADMIN)
        p2 = store.create_project("Two", ADMIN)
        store.create_release(p1["id"], "v1", ADMIN)
        self.assertEqual(store.create_release(p2["id"], "v1", ADMIN)["project_id"], p2["id"])

    def test_unknown_project_and_empty_version(self):
        """Core 5: unknown project -> NotFoundError; empty version -> ValidationError."""
        store, project = make_store()
        with self.assertRaises(NotFoundError):
            store.create_release("prj-999", "v1", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_release(project["id"], "", ADMIN)


if __name__ == "__main__":
    unittest.main()
