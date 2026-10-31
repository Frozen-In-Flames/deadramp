"""Groups tests.

Traces to: Core function -- Directory groups; contract for
``create_group/add_to_group/list_groups/list_group_members``.
"""

import unittest

from comm_helpers import OPERATOR, VIEWER, fresh_store
from comm.errors import NotFoundError, PermissionDenied, ValidationError


class TestGroups(unittest.TestCase):
    """Core: Groups."""

    def setUp(self):
        self.store = fresh_store()
        self.c1 = self.store.create_contact("A", {"email": "a@x.y"}, OPERATOR)
        self.c2 = self.store.create_contact("B", {"email": "b@x.y"}, OPERATOR)

    def test_create_shape(self):
        """Core: Groups. create_group returns grp-N with members []."""
        g = self.store.create_group("team", OPERATOR)
        self.assertEqual(g["id"], "grp-1")
        self.assertEqual(g["members"], [])
        self.assertEqual(g["created_by"], "bob")

    def test_add_and_list_members(self):
        """Core: Groups. add_to_group adds; list_group_members returns contact dicts."""
        g = self.store.create_group("team", OPERATOR)
        self.store.add_to_group(g["id"], self.c1["id"], OPERATOR)
        self.store.add_to_group(g["id"], self.c2["id"], OPERATOR)
        members = self.store.list_group_members(g["id"], VIEWER)
        self.assertEqual([m["id"] for m in members], [self.c1["id"], self.c2["id"]])
        self.assertEqual([g2["id"] for g2 in self.store.list_groups(VIEWER)], [g["id"]])

    def test_duplicate_membership_validation(self):
        """Core: Groups. Duplicate membership -> ValidationError."""
        g = self.store.create_group("team", OPERATOR)
        self.store.add_to_group(g["id"], self.c1["id"], OPERATOR)
        with self.assertRaises(ValidationError):
            self.store.add_to_group(g["id"], self.c1["id"], OPERATOR)

    def test_unknown_ids_not_found(self):
        """Core: Groups. Unknown group/contact in add_to_group -> NotFoundError; unknown group members -> NotFoundError."""
        g = self.store.create_group("team", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.add_to_group("grp-999", self.c1["id"], OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.add_to_group(g["id"], "ct-999", OPERATOR)
        with self.assertRaises(NotFoundError):
            self.store.list_group_members("grp-999", OPERATOR)

    def test_viewer_cannot_write_and_empty_name(self):
        """Core: Groups / Access control. Viewer group_write denied; empty name -> ValidationError, no id consumed."""
        with self.assertRaises(PermissionDenied):
            self.store.create_group("x", VIEWER)
        with self.assertRaises(ValidationError):
            self.store.create_group("", OPERATOR)
        self.assertEqual(self.store.create_group("ok", OPERATOR)["id"], "grp-1")


if __name__ == "__main__":
    unittest.main()
