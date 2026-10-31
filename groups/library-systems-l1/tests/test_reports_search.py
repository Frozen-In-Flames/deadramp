"""Reporting (counts only, no scores) and registry search."""
import unittest
from librarysys_helpers import BOB, DUE, seeded

class ReportSearchTests(unittest.TestCase):
    def setUp(self):
        self.store, self.lib, self.item = seeded()
        h = self.store.create_holding(self.lib["id"], self.item["id"], "h-1", "branch-a", 2, BOB)
        self.store.record_loan(self.lib["id"], h["id"], "loan-1", "patron-9", DUE, BOB)
    def test_report_counts(self):
        r = self.store.library_report(self.lib["id"], BOB)
        self.assertEqual(r["item_count"], 1); self.assertEqual(r["copies_total"], 2)
        self.assertEqual(r["available_copies_total"], 1); self.assertEqual(r["active_loans"], 1)
    def test_report_has_no_score_keys(self):
        r = self.store.library_report(self.lib["id"], BOB)
        self.assertFalse(any("score" in k or "rank" in k for k in r))
    def test_search(self):
        out = self.store.search_registry(BOB, "catalogued")
        self.assertEqual(len(out["items"]), 1)
        out = self.store.search_registry(BOB, "lib-main")
        self.assertEqual(len(out["libraries"]), 1)
if __name__ == "__main__": unittest.main()
