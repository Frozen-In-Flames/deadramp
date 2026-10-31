"""Core function 1: customer organizations & membership (AC-3)."""

import unittest

import mdm_helpers as H
from mdm.errors import PermissionDenied, ValidationError


class TestOrganizations(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()

    def test_create_shape_and_membership(self):
        org = self.store.get_organization(H.ADMIN, self.org["id"])
        self.assertEqual(
            set(org.keys()),
            {"id", "ref", "label", "owner", "members",
             "created_by", "created_utc"})
        self.assertEqual(org["ref"], H.ORG_REF)
        self.assertEqual(org["owner"], "bob")
        self.assertIn("bob", org["members"])
        self.assertIn("erin", org["members"])

    def test_duplicate_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, H.ORG_REF, "Copy")

    def test_empty_ref_and_label_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, "  ", "X")
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.MEMBER, "X-1", "")

    def test_outsider_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.store.get_organization(H.OUTSIDER, self.org["id"])
        self.assertEqual(self.store.list_organizations(H.OUTSIDER), [])

    def test_admin_reaches_without_membership(self):
        view = self.store.get_organization(H.ADMIN, self.org["id"])
        self.assertEqual(view["id"], self.org["id"])

    def test_add_member_and_update_label(self):
        self.store.add_member(H.ADMIN, self.org["id"], H.VIEWER.name)
        self.store.update_organization(H.MEMBER, self.org["id"], "Agency One (renamed)")
        view = self.store.get_organization(H.VIEWER, self.org["id"])
        self.assertEqual(view["label"], "Agency One (renamed)")

    def test_viewer_cannot_create_or_update(self):
        self.store.add_member(H.ADMIN, self.org["id"], H.VIEWER.name)
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(H.VIEWER, "NEW-1", "Nope")
        with self.assertRaises(PermissionDenied):
            self.store.update_organization(H.VIEWER, self.org["id"], "Nope")


if __name__ == "__main__":
    unittest.main()
