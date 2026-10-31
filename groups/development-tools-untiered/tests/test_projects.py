"""Project registry tests.

Traces to: Core function 1 (project registry, CM-6/SI-12) --
``prj-`` records with provenance.
"""

import unittest

from devtools_helpers import ADMIN, DEVELOPER, VIEWER, fresh_store
from devtools.errors import NotFoundError, PermissionDenied, ValidationError


class TestProjects(unittest.TestCase):
    """Core 1: project registry creation, shape, validation, RBAC."""

    def test_create_shape_and_ids(self):
        """Core 1: create_project returns prj-N shape with created_by/created_utc."""
        store = fresh_store()
        p1 = store.create_project("Alpha", ADMIN, description="d", repo_url="https://example.invalid/a")
        p2 = store.create_project("Beta", DEVELOPER)
        self.assertEqual(p1["id"], "prj-1")
        self.assertEqual(p2["id"], "prj-2")
        self.assertEqual(p1["description"], "d")
        self.assertEqual(p1["repo_url"], "https://example.invalid/a")
        self.assertIsNone(p2["description"])
        self.assertEqual(p1["created_by"], "alice")
        self.assertIn("created_utc", p1)

    def test_get_and_list(self):
        """Core 1: get_project / list_projects return the registry sorted by id."""
        store = fresh_store()
        store.create_project("Alpha", ADMIN)
        store.create_project("Beta", ADMIN)
        self.assertEqual(store.get_project("prj-1")["name"], "Alpha")
        self.assertEqual([p["name"] for p in store.list_projects()], ["Alpha", "Beta"])
        with self.assertRaises(NotFoundError):
            store.get_project("prj-999")

    def test_empty_name_validation_no_id_consumed(self):
        """Core 1 (SI-10): empty name -> ValidationError and no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_project("", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_project("   ", ADMIN)
        p = store.create_project("Ok", ADMIN)
        self.assertEqual(p["id"], "prj-1")

    def test_viewer_write_denied(self):
        """Core 1/9 (AC-3): viewer may read but not create a project."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_project("Nope", VIEWER)
        self.assertEqual(store.list_projects(ADMIN), [])
        p = store.create_project("Real", ADMIN)
        self.assertEqual(store.get_project(p["id"], VIEWER)["name"], "Real")

    def test_plain_string_actor_carries_identity_no_role(self):
        """Core 1/9: plain-string actor carries identity but no role (service enforces)."""
        store = fresh_store()
        p = store.create_project("Stringy", "mallory-string")
        self.assertEqual(p["created_by"], "mallory-string")


if __name__ == "__main__":
    unittest.main()
