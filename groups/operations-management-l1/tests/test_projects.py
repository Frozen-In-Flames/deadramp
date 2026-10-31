"""Project tests.

Traces to: Core function 2 -- Projects; contract for
``OpsStore.create_project/add_person_to_project/get_project/
list_projects/list_project_members``; AC-3/AC-6, IA-2 (hooks).
"""

import unittest

from opsmgmt_helpers import OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestProjects(unittest.TestCase):
    """Core 2: Projects."""

    def test_create_project_shape_and_id(self):
        """Core 2: Projects. create_project returns proj- id, org link, empty members, provenance."""
        store = fresh_store()
        org = store.create_organization("Acme", OPERATOR)
        project = store.create_project("Alpha", OPERATOR, org_id=org["id"], attributes={"phase": "1"})
        self.assertEqual(project["id"], "proj-1")
        self.assertEqual(project["name"], "Alpha")
        self.assertEqual(project["org_id"], org["id"])
        self.assertEqual(project["members"], [])
        self.assertEqual(project["attributes"], {"phase": "1"})
        self.assertEqual(project["created_by"], "bob")

    def test_create_project_defaults_no_org(self):
        """Core 2: Projects. org_id defaults to None, attributes to {}."""
        store = fresh_store()
        project = store.create_project("Alpha", OPERATOR)
        self.assertIsNone(project["org_id"])
        self.assertEqual(project["attributes"], {})

    def test_create_project_unknown_org_and_validation_no_id(self):
        """Core 2: Projects (SI-10). Unknown org -> NotFoundError; empty name/bad attributes -> ValidationError; no id consumed."""
        store = fresh_store()
        with self.assertRaises(NotFoundError):
            store.create_project("Alpha", OPERATOR, org_id="org-999")
        with self.assertRaises(ValidationError):
            store.create_project("", OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_project("Alpha", OPERATOR, attributes="x")
        self.assertEqual(store.create_project("Alpha", OPERATOR)["id"], "proj-1")

    def test_add_person_and_list_members(self):
        """Core 2: Projects. add_person_to_project appends; list_project_members returns person dicts."""
        store, person, organization, project = make_store()
        self.assertEqual(store.get_project(project["id"], VIEWER)["members"], [person["id"]])
        members = store.list_project_members(project["id"], VIEWER)
        self.assertEqual([m["id"] for m in members], [person["id"]])
        self.assertEqual(members[0]["name"], person["name"])
        self.assertEqual(members[0]["reference"], person["reference"])

    def test_duplicate_membership_validation(self):
        """Core 2: Projects. Duplicate membership -> ValidationError."""
        store, person, organization, project = make_store()
        with self.assertRaises(ValidationError):
            store.add_person_to_project(project["id"], person["id"], OPERATOR)

    def test_unknown_ids_not_found(self):
        """Core 2: Projects. Unknown project/person ids -> NotFoundError."""
        store, person, organization, project = make_store()
        with self.assertRaises(NotFoundError):
            store.add_person_to_project("proj-999", person["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            store.add_person_to_project(project["id"], "per-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.list_project_members("proj-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            store.get_project("proj-999", OPERATOR)

    def test_list_projects_and_get(self):
        """Core 2: Projects. list_projects in creation order; viewer may read."""
        store = fresh_store()
        p1 = store.create_project("a", OPERATOR)
        p2 = store.create_project("b", OPERATOR)
        self.assertEqual((p1["id"], p2["id"]), ("proj-1", "proj-2"))
        self.assertEqual([p["id"] for p in store.list_projects(VIEWER)], ["proj-1", "proj-2"])
        self.assertEqual(store.get_project(p2["id"], VIEWER)["name"], "b")

    def test_viewer_cannot_write_project(self):
        """Core 2/11: Projects/RBAC. Viewer create/add -> PermissionDenied."""
        store, person, organization, project = make_store()
        with self.assertRaises(PermissionDenied):
            store.create_project("x", VIEWER)
        person2 = store.create_person("Eve", OPERATOR)
        with self.assertRaises(PermissionDenied):
            store.add_person_to_project(project["id"], person2["id"], VIEWER)

    def test_project_copies_are_copies(self):
        """Core 2: Projects. Mutating a returned project's members/attributes does not mutate the store."""
        store, person, organization, project = make_store()
        project["members"].append("per-999")
        project["attributes"]["phase"] = "hacked"
        again = store.get_project(project["id"], OPERATOR)
        self.assertEqual(again["members"], [person["id"]])
        self.assertEqual(again["attributes"], {"phase": "1"})


if __name__ == "__main__":
    unittest.main()
