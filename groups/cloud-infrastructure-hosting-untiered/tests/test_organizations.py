"""Organizations: registry, membership boundary, creator-or-admin
member gate, role enforcement (Core function 1 + substrate)."""

import unittest

import cloudinfra_helpers as H
from cloudinfra.errors import NotFoundError, PermissionDenied, ValidationError


class TestOrganizations(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = H.make_store()

    def test_create_organization_shape(self):
        org = self.store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
        self.assertEqual(org["id"], "org-1")
        self.assertEqual(org["org_ref"], H.ORG_REF)
        self.assertEqual(org["members"], ["alice"])
        self.assertEqual(org["created_by"], "alice")
        self.assertIn("created_utc", org)

    def test_duplicate_org_ref_rejected_and_consumes_no_id(self):
        self.store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
        with self.assertRaises(ValidationError):
            self.store.create_organization(H.ORG_REF, "Copy", H.ADMIN)
        second = self.store.create_organization("org-beta", "Beta", H.ADMIN)
        self.assertEqual(second["id"], "org-2")

    def test_member_role_cannot_create_organization(self):
        # org_write is admin-only; a User actor is role-checked in the store.
        with self.assertRaises(PermissionDenied):
            self.store.create_organization("org-x", "X", H.MEMBER)

    def test_string_actor_carries_identity_only(self):
        org = self.store.create_organization("org-str", "Str Org", "dave")
        self.assertEqual(org["created_by"], "dave")
        self.assertEqual(org["members"], ["dave"])

    def test_add_member_by_creator(self):
        org = self.store.create_organization(H.ORG_REF, H.ORG_LABEL, H.ADMIN)
        updated = self.store.add_member(org["id"], "bob", H.ADMIN)
        self.assertEqual(updated["members"], ["alice", "bob"])

    def test_add_member_by_non_creator_member_denied(self):
        org = H.make_org(self.store)
        # bob is a member but neither creator nor admin.
        with self.assertRaises(PermissionDenied):
            self.store.add_member(org["id"], "erin", H.MEMBER)

    def test_add_member_duplicate_rejected(self):
        org = H.make_org(self.store)
        with self.assertRaises(ValidationError):
            self.store.add_member(org["id"], "bob", H.ADMIN)

    def test_add_member_to_missing_org(self):
        with self.assertRaises(NotFoundError):
            self.store.add_member("org-99", "erin", H.ADMIN)

    def test_list_organizations_scoped_by_membership(self):
        H.make_org(self.store)
        self.assertEqual(len(self.store.list_organizations(H.MEMBER)), 1)
        self.assertEqual(self.store.list_organizations(H.OUTSIDER), [])
        self.assertEqual(len(self.store.list_organizations(H.ADMIN)), 1)

    def test_get_organization_denied_for_non_member(self):
        org = H.make_org(self.store)
        with self.assertRaises(PermissionDenied):
            self.store.get_organization(org["id"], H.OUTSIDER)
        self.assertEqual(
            self.store.get_organization(org["id"], H.VIEWER)["id"], org["id"])

    def test_mutations_are_audited(self):
        org = H.make_org(self.store)
        actions = [e["action"] for e in self.audit.entries()]
        self.assertIn("organization_create", actions)
        self.assertIn("member_add", actions)
        self.assertTrue(all(e["target"] for e in self.audit.entries()))


if __name__ == "__main__":
    unittest.main()
