"""Privacy discipline: patrons are opaque references; no store
parameter or record field can hold a real name or contact detail."""
import inspect, unittest
from librarysys.store import LibrarySysStore
from librarysys_helpers import BOB, DUE, seeded

BANNED = ("email", "phone", "address", "ssn", "contact", "full_name", "patron_name", "first_name", "last_name")
class PrivacyTests(unittest.TestCase):
    def test_no_banned_parameters(self):
        for name, fn in inspect.getmembers(LibrarySysStore, predicate=inspect.isfunction):
            if name.startswith("_"): continue
            for param in inspect.signature(fn).parameters:
                self.assertNotIn(param.lower(), BANNED, "%s.%s" % (name, param))
    def test_record_shapes_have_no_identity_fields(self):
        store, lib, item = seeded()
        h = store.create_holding(lib["id"], item["id"], "h-1", "branch-a", 1, BOB)
        loan = store.record_loan(lib["id"], h["id"], "loan-1", "patron-9", DUE, BOB)
        for rec in (item, h, loan):
            for key in rec:
                self.assertNotIn(key.lower(), BANNED)
        self.assertEqual(loan["patron_ref"], "patron-9")
if __name__ == "__main__": unittest.main()
