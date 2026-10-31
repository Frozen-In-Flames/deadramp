"""Catalogue + holdings: traces to the library_management claim
(SirsiDynix) and the platform_services claim (Ex Libris registry)."""
import unittest
from librarysys_helpers import ALICE, BOB, CAROL, seeded
from librarysys.errors import NotFoundError, PermissionDenied, ValidationError

class CatalogueTests(unittest.TestCase):
    def setUp(self): self.store, self.lib, self.item = seeded()
    def test_library_shape(self):
        self.assertEqual(self.lib["library_ref"], "lib-main")
        self.assertIn("alice", self.lib["members"])
    def test_duplicate_library_ref_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.create_library("lib-main", "Again", ALICE)
    def test_non_member_denied(self):
        from librarysys.access import User
        with self.assertRaises(PermissionDenied):
            self.store.list_items(self.lib["id"], User("mallory", "member"))
    def test_viewer_cannot_write(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_item(self.lib["id"], "item-2", "X", CAROL)
    def test_item_shape_and_duplicate(self):
        self.assertEqual(set(self.item), {"id","lib_id","item_ref","title","format_label","created_by","created_utc"})
        with self.assertRaises(ValidationError):
            self.store.create_item(self.lib["id"], "item-1", "Dup", BOB)
    def test_holding_quantity_validation(self):
        for bad in (0, -1, 1.5, True, "2"):
            with self.assertRaises(ValidationError):
                self.store.create_holding(self.lib["id"], self.item["id"], "h-bad", "branch-a", bad, BOB)
    def test_available_copies_derived_never_stored(self):
        h = self.store.create_holding(self.lib["id"], self.item["id"], "h-1", "branch-a", 3, BOB)
        view = self.store.get_holding(self.lib["id"], h["id"], BOB)
        self.assertEqual(view["available_copies"], 3)
        stored = self.store._holdings[h["id"]]
        self.assertNotIn("available_copies", stored)
    def test_missing_item_holding_rejected(self):
        with self.assertRaises(NotFoundError):
            self.store.create_holding(self.lib["id"], "cat-999", "h-x", "branch-a", 1, BOB)
if __name__ == "__main__": unittest.main()
