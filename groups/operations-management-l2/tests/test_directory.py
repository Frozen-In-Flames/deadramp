"""Directory tests: persons and organizations.

Traces to: Core function 1 -- Directory; contract for
``OpsStore.create_person/create_organization/get_*/list_*``.
Design constraint traced here: a person/organization ``reference``
is an opaque external reference string, never a real personal
identifier.
"""

import unittest

from opsmgmt_helpers import ADMIN, OPERATOR, VIEWER, fresh_store, make_store
from opsmgmt.errors import NotFoundError, PermissionDenied, ValidationError


class TestPersons(unittest.TestCase):
    """Core 1: Directory -- persons."""

    def test_create_person_shape_and_id(self):
        """Core 1: Directory. create_person returns per- id, name, reference, attributes, provenance."""
        store = fresh_store()
        person = store.create_person("Pat", OPERATOR, reference="EXT-9", attributes={"team": "ops"})
        self.assertEqual(person["id"], "per-1")
        self.assertEqual(person["name"], "Pat")
        self.assertEqual(person["reference"], "EXT-9")
        self.assertEqual(person["attributes"], {"team": "ops"})
        self.assertEqual(person["created_by"], "bob")
        self.assertIn("created_utc", person)

    def test_create_person_defaults(self):
        """Core 1: Directory. reference defaults to None, attributes to {}."""
        store = fresh_store()
        person = store.create_person("Pat", OPERATOR)
        self.assertIsNone(person["reference"])
        self.assertEqual(person["attributes"], {})

    def test_get_and_list_persons(self):
        """Core 1: Directory. get_person/list_persons return copies sorted by id; viewer may read."""
        store, person, organization, project = make_store()
        self.assertEqual(store.get_person(person["id"], VIEWER)["id"], person["id"])
        self.assertEqual([p["id"] for p in store.list_persons(VIEWER)], [person["id"]])
        with self.assertRaises(NotFoundError):
            store.get_person("per-999", VIEWER)

    def test_person_copies_are_copies(self):
        """Core 1: Directory. Mutating a returned person does not mutate the store."""
        store = fresh_store()
        person = store.create_person("Pat", OPERATOR, attributes={"k": "v"})
        person["name"] = "hacked"
        person["attributes"]["k"] = "hacked"
        again = store.get_person(person["id"], OPERATOR)
        self.assertEqual(again["name"], "Pat")
        self.assertEqual(again["attributes"], {"k": "v"})

    def test_person_validation_and_no_id_on_failure(self):
        """Core 1: Directory (SI-10). Empty name / non-string reference / bad attributes -> ValidationError, no id consumed."""
        store = fresh_store()
        for bad_name in ("", "  ", None, 42):
            with self.assertRaises(ValidationError):
                store.create_person(bad_name, OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_person("Pat", OPERATOR, reference=12345)
        with self.assertRaises(ValidationError):
            store.create_person("Pat", OPERATOR, attributes=["not-a-dict"])
        person = store.create_person("Pat", OPERATOR)
        self.assertEqual(person["id"], "per-1")

    def test_viewer_cannot_create_person(self):
        """Core 1/11: Directory/RBAC. Viewer create_person -> PermissionDenied, no id consumed."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_person("Pat", VIEWER)
        self.assertEqual(store.create_person("Pat", OPERATOR)["id"], "per-1")


class TestOrganizations(unittest.TestCase):
    """Core 1: Directory -- organizations (incl. contractor/vendor orgs)."""

    def test_create_organization_shape_and_id(self):
        """Core 1: Directory. create_organization returns org- id with opaque reference and attributes."""
        store = fresh_store()
        org = store.create_organization("Acme Vendor", OPERATOR, reference="ORG-9", attributes={"kind": "vendor"})
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(org["name"], "Acme Vendor")
        self.assertEqual(org["reference"], "ORG-9")
        self.assertEqual(org["attributes"], {"kind": "vendor"})
        self.assertEqual(org["created_by"], "bob")

    def test_create_organization_defaults(self):
        """Core 1: Directory. reference defaults to None, attributes to {}."""
        store = fresh_store()
        org = store.create_organization("Acme", OPERATOR)
        self.assertIsNone(org["reference"])
        self.assertEqual(org["attributes"], {})

    def test_get_and_list_organizations(self):
        """Core 1: Directory. get_organization/list_organizations work for viewer; unknown id -> NotFoundError."""
        store, person, organization, project = make_store()
        self.assertEqual(store.get_organization(organization["id"], VIEWER)["id"], organization["id"])
        self.assertEqual([o["id"] for o in store.list_organizations(VIEWER)], [organization["id"]])
        with self.assertRaises(NotFoundError):
            store.get_organization("org-999", VIEWER)

    def test_organization_validation_and_no_id_on_failure(self):
        """Core 1: Directory (SI-10). Empty name / non-string reference / bad attributes -> ValidationError, no id consumed."""
        store = fresh_store()
        with self.assertRaises(ValidationError):
            store.create_organization("", OPERATOR)
        with self.assertRaises(ValidationError):
            store.create_organization("Acme", OPERATOR, reference=12345)
        with self.assertRaises(ValidationError):
            store.create_organization("Acme", OPERATOR, attributes="x")
        self.assertEqual(store.create_organization("Acme", OPERATOR)["id"], "org-1")

    def test_organization_copies_are_copies(self):
        """Core 1: Directory. Mutating a returned organization's attributes does not mutate the store."""
        store = fresh_store()
        org = store.create_organization("Acme", OPERATOR, attributes={"k": "v"})
        org["attributes"]["k"] = "hacked"
        self.assertEqual(store.get_organization(org["id"], OPERATOR)["attributes"], {"k": "v"})

    def test_viewer_cannot_create_organization(self):
        """Core 1/11: Directory/RBAC. Viewer create_organization -> PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_organization("Acme", VIEWER)
        self.assertEqual(store.create_organization("Acme", ADMIN)["id"], "org-1")


if __name__ == "__main__":
    unittest.main()
