"""Negative control: a mutant store whose availability seam performs
no check accepts an over-quantity loan. The canonical expectation is
shown to reject it. Mutation-verified: see tests/README.md."""
import unittest
from librarysys.store import LibrarySysStore
from librarysys_helpers import BOB, DUE, seeded
from librarysys.errors import ValidationError

class MutantStore(LibrarySysStore):
    def _check_holding_availability(self, holding, active_loan_count):
        return None

class NegativeControlTests(unittest.TestCase):
    def _setup(self, store):
        from librarysys_helpers import ALICE
        lib = store.create_library("lib-m", "M", ALICE)
        store.add_member(lib["id"], "bob", ALICE)
        item = store.create_item(lib["id"], "item-1", "Work", BOB)
        h = store.create_holding(lib["id"], item["id"], "h-1", "branch-a", 1, BOB)
        return lib, h
    def test_mutant_accepts_over_quantity_loan(self):
        store = MutantStore()
        lib, h = self._setup(store)
        store.record_loan(lib["id"], h["id"], "loan-1", "patron-9", DUE, BOB)
        store.record_loan(lib["id"], h["id"], "loan-2", "patron-8", DUE, BOB)  # mutant: accepted
        self.assertEqual(len(store.list_loans(lib["id"], BOB)), 2)
    def test_canonical_rejects_over_quantity_loan(self):
        store, lib, item = seeded()
        h = store.create_holding(lib["id"], item["id"], "h-1", "branch-a", 1, BOB)
        store.record_loan(lib["id"], h["id"], "loan-1", "patron-9", DUE, BOB)
        with self.assertRaises(ValidationError):
            store.record_loan(lib["id"], h["id"], "loan-2", "patron-8", DUE, BOB)
if __name__ == "__main__": unittest.main()
