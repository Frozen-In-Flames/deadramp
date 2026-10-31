"""Core: Organization registry (opaque references). Traces to
UNION-SPEC core function 2's registry substrate (organizations
known only by a caller-supplied opaque ``ref`` and a label). The
record shape is pinned: no field can hold a real identifier."""

import unittest

import research_helpers as H
from research.errors import NotFoundError, PermissionDenied, ValidationError

EXPECTED_KEYS = {"id", "ref", "label", "created_by", "created_utc"}


class TestOrganizations(unittest.TestCase):
    def setUp(self):
        self.store = H.fresh_store()

    def test_create_shape_is_pinned(self):
        org = self.store.create_organization(H.MEMBER, "ORG-1", "Alpha")
        self.assertEqual(set(org.keys()), EXPECTED_KEYS)
        self.assertTrue(org["id"].startswith("org-"))
        self.assertEqual(org["created_by"], "bob")

    def test_duplicate_ref_rejected(self):
        self.store.create_organization(H.MEMBER, "ORG-1", "Alpha")
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, "ORG-1", "Beta")

    def test_empty_ref_or_label_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, "", "Alpha")
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, "ORG-1", " ")

    def test_update_label(self):
        org = self.store.create_organization(H.MEMBER, "ORG-1", "Alpha")
        updated = self.store.update_organization(H.MEMBER, org["id"],
                                                 "Alpha II")
        self.assertEqual(updated["label"], "Alpha II")
        self.assertEqual(set(updated.keys()), EXPECTED_KEYS)
        self.assertEqual(
            self.store.get_organization(H.MEMBER, org["id"])["label"],
            "Alpha II")

    def test_viewer_cannot_create_or_update(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(H.VIEWER, "ORG-1", "Alpha")
        org = self.store.create_organization(H.MEMBER, "ORG-1", "Alpha")
        with self.assertRaises(PermissionDenied):
            self.store.update_organization(H.VIEWER, org["id"], "Nope")

    def test_get_and_list(self):
        org = self.store.create_organization(H.MEMBER, "ORG-1", "Alpha")
        self.assertEqual(
            self.store.get_organization(H.VIEWER, org["id"])["ref"], "ORG-1")
        self.assertEqual(len(self.store.list_organizations(H.VIEWER)), 1)
        with self.assertRaises(NotFoundError):
            self.store.get_organization(H.MEMBER, "org-99")


if __name__ == "__main__":
    unittest.main()
