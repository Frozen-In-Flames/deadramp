import unittest

from travel.errors import NotFoundError, PermissionDenied

from travel_helpers import ADMIN, MEMBER, OUTSIDER, VIEWER, make_store


class TestOrganizations(unittest.TestCase):
    def setUp(self):
        self.store, self.org = make_store()

    def test_create_and_get(self):
        got = self.store.get_organization(MEMBER, self.org["id"])
        self.assertEqual(got["ref"], "ORG-100")
        self.assertEqual(got["label"], "Agency One")
        self.assertEqual(got["created_by"], "alice")

    def test_creator_is_member(self):
        members = self.store.list_members(ADMIN, self.org["id"])
        self.assertIn("alice", members)
        self.assertIn("bob", members)

    def test_outsider_cannot_read(self):
        with self.assertRaises(PermissionDenied):
            self.store.get_organization(OUTSIDER, self.org["id"])

    def test_outsider_sees_no_organizations(self):
        self.assertEqual(self.store.list_organizations(OUTSIDER), [])

    def test_admin_sees_all_organizations(self):
        self.store.create_organization(MEMBER, "ORG-200", "Agency Two")
        labels = {o["label"] for o in self.store.list_organizations(ADMIN)}
        self.assertEqual(labels, {"Agency One", "Agency Two"})

    def test_missing_organization(self):
        with self.assertRaises(NotFoundError):
            self.store.get_organization(ADMIN, "org-999")

    def test_member_cannot_manage_members(self):
        with self.assertRaises(PermissionDenied):
            self.store.add_member(MEMBER, self.org["id"], "erin")

    def test_admin_adds_member_who_can_then_read(self):
        self.store.add_member(ADMIN, self.org["id"], OUTSIDER.name)
        got = self.store.get_organization(OUTSIDER, self.org["id"])
        self.assertEqual(got["id"], self.org["id"])

    def test_viewer_cannot_create_organization(self):
        # create_organization checks the "enter" action for User actors.
        with self.assertRaises(PermissionDenied):
            self.store.create_organization(VIEWER, "ORG-300", "Agency Three")


if __name__ == "__main__":
    unittest.main()
