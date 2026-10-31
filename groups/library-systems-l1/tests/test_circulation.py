"""Circulation records: traces to the library_management claim.
Loans enforce the availability seam; overdue and queue position are
derived on read."""
import unittest
from librarysys_helpers import BOB, CAROL, DUE, NOW_LATE, PAST, seeded
from librarysys.errors import PermissionDenied, ValidationError

class CirculationTests(unittest.TestCase):
    def setUp(self):
        self.store, self.lib, self.item = seeded()
        self.h = self.store.create_holding(self.lib["id"], self.item["id"], "h-1", "branch-a", 1, BOB)
    def test_loan_and_return(self):
        loan = self.store.record_loan(self.lib["id"], self.h["id"], "loan-1", "patron-9", DUE, BOB)
        self.assertEqual(loan["status"], "active")
        self.assertEqual(self.store.get_holding(self.lib["id"], self.h["id"], BOB)["available_copies"], 0)
        done = self.store.return_loan(self.lib["id"], loan["id"], BOB)
        self.assertEqual(done["status"], "returned")
        self.assertEqual(self.store.get_holding(self.lib["id"], self.h["id"], BOB)["available_copies"], 1)
        with self.assertRaises(ValidationError):
            self.store.return_loan(self.lib["id"], loan["id"], BOB)
    def test_availability_seam_blocks_second_loan(self):
        self.store.record_loan(self.lib["id"], self.h["id"], "loan-1", "patron-9", DUE, BOB)
        with self.assertRaises(ValidationError):
            self.store.record_loan(self.lib["id"], self.h["id"], "loan-2", "patron-8", DUE, BOB)
    def test_overdue_derived_never_stored(self):
        loan = self.store.record_loan(self.lib["id"], self.h["id"], "loan-1", "patron-9", PAST, BOB)
        self.assertTrue(self.store.get_loan(self.lib["id"], loan["id"], BOB, now=NOW_LATE)["overdue"])
        self.assertNotIn("overdue", self.store._loans[loan["id"]])
    def test_bad_due_at_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_loan(self.lib["id"], self.h["id"], "loan-1", "patron-9", "not-a-date", BOB)
    def test_viewer_cannot_loan(self):
        with self.assertRaises(PermissionDenied):
            self.store.record_loan(self.lib["id"], self.h["id"], "loan-1", "patron-9", DUE, CAROL)
    def test_holds_queue_derived(self):
        h1 = self.store.place_hold(self.lib["id"], self.item["id"], "hold-1", "patron-9", BOB)
        self.store.place_hold(self.lib["id"], self.item["id"], "hold-2", "patron-8", BOB)
        views = {v["hold_ref"]: v for v in self.store.list_holds(self.lib["id"], BOB)}
        self.assertEqual(views["hold-1"]["queue_position"], 1)
        self.assertEqual(views["hold-2"]["queue_position"], 2)
        self.assertNotIn("queue_position", self.store._holds[h1["id"]])
        self.store.fulfill_hold(self.lib["id"], h1["id"], BOB)
        views = {v["hold_ref"]: v for v in self.store.list_holds(self.lib["id"], BOB)}
        self.assertEqual(views["hold-2"]["queue_position"], 1)
        self.assertIsNone(views["hold-1"]["queue_position"])
    def test_hold_close_guards(self):
        h1 = self.store.place_hold(self.lib["id"], self.item["id"], "hold-1", "patron-9", BOB)
        self.store.cancel_hold(self.lib["id"], h1["id"], BOB)
        with self.assertRaises(ValidationError):
            self.store.cancel_hold(self.lib["id"], h1["id"], BOB)
if __name__ == "__main__": unittest.main()
