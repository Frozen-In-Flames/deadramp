"""Core 1 (Customer organizations & membership) / AC-2, AC-3:
organization record shape, uniqueness, and the membership
boundary -- the records form of the fork's contract-gated access
claim.
"""

import unittest

import sysadmin_helpers as H
from sysadmin.errors import PermissionDenied, ValidationError

ORG_KEYS = {"id", "ref", "label", "owner", "members", "created_utc"}


class TestOrganizations(unittest.TestCase):
    def test_record_shape_pinned(self):
        store = H.fresh_store()
        org = H.make_org(store)
        self.assertEqual(set(org.keys()), ORG_KEYS)
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(org["owner"], "bob")
        self.assertEqual(org["members"], ["bob"])

    def test_duplicate_ref_rejected(self):
        store = H.fresh_store()
        H.make_org(store)
        with self.assertRaises(ValidationError):
            H.make_org(store, actor=H.STAFF)

    def test_creator_becomes_member_and_can_read(self):
        store, org = H.make_store()
        view = store.get_organization(H.MEMBER, org["id"])
        self.assertEqual(view["ref"], H.ORG_REF)

    def test_outsider_cannot_read(self):
        store, org = H.make_store()
        with self.assertRaises(PermissionDenied):
            store.get_organization(H.OUTSIDER, org["id"])

    def test_platform_admin_reads_without_membership(self):
        store, org = H.make_store()
        view = store.get_organization(H.ADMIN, org["id"])
        self.assertEqual(view["id"], org["id"])

    def test_list_organizations_scoped_to_membership(self):
        store, org = H.make_store()
        self.assertEqual(
            [o["id"] for o in store.list_organizations(H.MEMBER)], [org["id"]])
        self.assertEqual(store.list_organizations(H.OUTSIDER), [])
        self.assertEqual(
            [o["id"] for o in store.list_organizations(H.ADMIN)], [org["id"]])

    def test_add_member_and_viewer_stays_read_only(self):
        store, org = H.make_store()
        store.add_member(H.ADMIN, org["id"], H.VIEWER.name)
        view = store.get_organization(H.VIEWER, org["id"])
        self.assertIn("carol", view["members"])
        with self.assertRaises(PermissionDenied):
            store.create_system(H.VIEWER, org["id"], "SYS-X", "x",
                                "operating_system", "PLAT-A")


if __name__ == "__main__":
    unittest.main()
