"""Core functions 1-3: organization, retention-policy, and
collection registries -- pinned record shapes, ref uniqueness,
policy immutability, and integer validation (SI-10).
"""

import unittest

from storage.errors import NotFoundError, ValidationError

from storage_helpers import (ADMIN, VIEWER, make_collection, make_org,
                             make_policy, make_store)

ORG_KEYS = {"id", "ref", "label", "created_by", "created_utc"}
POLICY_KEYS = {"id", "label", "retention_days", "created_by", "created_utc"}
COLLECTION_KEYS = {"id", "org_id", "label", "policy_id", "format_label",
                   "created_by", "created_utc"}


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()

    def test_organization_shape_and_uniqueness(self):
        org = make_org(self.store)
        self.assertEqual(set(org), ORG_KEYS)
        self.assertEqual(org["id"], "org-1")
        with self.assertRaises(ValidationError):
            self.store.create_organization(ADMIN, org["ref"], "Duplicate")
        # the failed create consumed no id
        second = self.store.create_organization(ADMIN, "ORG-0002", "Second")
        self.assertEqual(second["id"], "org-2")

    def test_organization_validation(self):
        for ref, label in [(None, "x"), ("", "x"), ("x", " "), (7, "x")]:
            with self.assertRaises(ValidationError):
                self.store.create_organization(ADMIN, ref, label)
        self.assertEqual(self.store.list_organizations(ADMIN), [])

    def test_policy_shape_and_integer_days(self):
        policy = make_policy(self.store)
        self.assertEqual(set(policy), POLICY_KEYS)
        self.assertEqual(policy["retention_days"], 30)
        for bad in (30.0, True, "30", 0, -5, None):
            with self.assertRaises(ValidationError):
                self.store.create_policy(ADMIN, "bad", bad)
        self.assertEqual(len(self.store.list_policies(ADMIN)), 1)

    def test_policies_are_immutable_records(self):
        # There is deliberately no update operation: a derivation
        # must always be reproducible against the named policy.
        self.assertFalse(hasattr(self.store, "update_policy"))
        self.assertFalse(hasattr(self.store, "delete_policy"))

    def test_collection_shape_and_links(self):
        org = make_org(self.store)
        policy = make_policy(self.store)
        collection = make_collection(self.store, org, policy)
        self.assertEqual(set(collection), COLLECTION_KEYS)
        self.assertEqual(collection["org_id"], org["id"])
        self.assertEqual(collection["policy_id"], policy["id"])
        with self.assertRaises(NotFoundError):
            self.store.create_collection(ADMIN, "org-99", "x",
                                         policy["id"], "native")
        with self.assertRaises(NotFoundError):
            self.store.create_collection(ADMIN, org["id"], "x",
                                         "pol-99", "native")

    def test_get_and_list(self):
        org = make_org(self.store)
        policy = make_policy(self.store)
        collection = make_collection(self.store, org, policy)
        self.assertEqual(self.store.get_organization(ADMIN, org["id"]), org)
        self.assertEqual(self.store.get_policy(ADMIN, policy["id"]), policy)
        self.assertEqual(
            self.store.get_collection(ADMIN, collection["id"]), collection)
        self.assertEqual(
            self.store.list_collections(ADMIN, org_id=org["id"]),
            [collection])
        with self.assertRaises(NotFoundError):
            self.store.get_collection(ADMIN, "col-99")

    def test_viewer_cannot_register(self):
        from storage.errors import PermissionDenied
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(VIEWER, "ORG-X", "nope")
        with self.assertRaises(PermissionDenied):
            self.store.create_policy(VIEWER, "nope", 30)
        org = make_org(self.store)
        policy = make_policy(self.store)
        with self.assertRaises(PermissionDenied):
            self.store.create_collection(VIEWER, org["id"], "nope",
                                         policy["id"], "native")
        # reads are open to the viewer role
        self.assertEqual(self.store.list_organizations(VIEWER), [org])


if __name__ == "__main__":
    unittest.main()
