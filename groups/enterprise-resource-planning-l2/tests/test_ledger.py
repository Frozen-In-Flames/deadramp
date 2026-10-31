"""Core function 4: general-ledger records and the
balanced-entry rule -- THE SIGNATURE INVARIANT (CM-6, AU-2/AU-3,
SI-10).

An entry is recorded only when it balances: every line one-sided,
total debits equal total credits, total positive. Amounts are
integer cents; booleans, floats, and strings are rejected at the
boundary. The derived totals in the entry view are computed at
read; the stored record carries no total keys.
"""

import unittest

from erp.errors import NotFoundError, PermissionDenied, ValidationError
from erp.store import _check_entry_balanced

from erp_helpers import (BALANCED_LINES, OPERATOR, UNBALANCED_LINES,
                         VIEWER, make_entry, make_org, make_store)


class SeamTests(unittest.TestCase):
    def test_seam_accepts_a_balanced_entry(self):
        self.assertIsNone(_check_entry_balanced(BALANCED_LINES))

    def test_seam_refuses_unequal_totals(self):
        with self.assertRaises(ValidationError):
            _check_entry_balanced(UNBALANCED_LINES)

    def test_seam_refuses_two_sided_and_zero_lines(self):
        with self.assertRaises(ValidationError):
            _check_entry_balanced([
                {"account_ref": "A", "debit_cents": 5, "credit_cents": 5},
                {"account_ref": "B", "debit_cents": 0, "credit_cents": 0},
            ])

    def test_seam_refuses_a_zero_total(self):
        with self.assertRaises(ValidationError):
            _check_entry_balanced([
                {"account_ref": "A", "debit_cents": 0, "credit_cents": 0},
            ])


class LedgerEntryTests(unittest.TestCase):
    def test_balanced_entry_records_with_derived_totals(self):
        store, _ = make_store()
        org = make_org(store)
        entry = make_entry(store, org)
        self.assertEqual(entry["total_debits_cents"], 12500)
        self.assertEqual(entry["total_credits_cents"], 12500)
        stored = store._ledger_entries[entry["id"]]
        self.assertNotIn("total_debits_cents", stored)
        self.assertNotIn("total_credits_cents", stored)
        self.assertEqual(
            set(stored.keys()),
            {"id", "org_id", "entry_ref", "memo_label", "lines", "seq",
             "created_by", "created_utc"})

    def test_unbalanced_entry_is_refused_whole(self):
        store, _ = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            make_entry(store, org, lines=UNBALANCED_LINES)
        self.assertEqual(store.list_ledger_entries(OPERATOR), [])
        # the refused entry consumed no id
        entry = make_entry(store, org, ref="JE-0002")
        self.assertEqual(entry["id"], "led-1")

    def test_amount_types_are_rejected_at_the_boundary(self):
        store, _ = make_store()
        org = make_org(store)
        for bad in (10.5, True, "100", None):
            lines = [
                {"account_ref": "A", "debit_cents": bad, "credit_cents": 0},
                {"account_ref": "B", "debit_cents": 0, "credit_cents": 100},
            ]
            with self.assertRaises(ValidationError, msg=repr(bad)):
                make_entry(store, org, lines=lines)
        self.assertEqual(store.list_ledger_entries(OPERATOR), [])

    def test_negative_amounts_refused(self):
        store, _ = make_store()
        org = make_org(store)
        lines = [
            {"account_ref": "A", "debit_cents": -100, "credit_cents": 0},
            {"account_ref": "B", "debit_cents": 0, "credit_cents": -100},
        ]
        with self.assertRaises(ValidationError):
            make_entry(store, org, lines=lines)

    def test_empty_and_malformed_lines_refused(self):
        store, _ = make_store()
        org = make_org(store)
        with self.assertRaises(ValidationError):
            make_entry(store, org, lines=[])
        with self.assertRaises(ValidationError):
            make_entry(store, org, lines=[{"debit_cents": 1}])
        with self.assertRaises(ValidationError):
            make_entry(store, org, lines="not-a-list")

    def test_entry_ref_unique_per_org(self):
        store, _ = make_store()
        org = make_org(store)
        make_entry(store, org)
        with self.assertRaises(ValidationError):
            make_entry(store, org)

    def test_multi_line_entry_balances_on_totals(self):
        store, _ = make_store()
        org = make_org(store)
        lines = [
            {"account_ref": "A", "debit_cents": 700, "credit_cents": 0},
            {"account_ref": "B", "debit_cents": 300, "credit_cents": 0},
            {"account_ref": "C", "debit_cents": 0, "credit_cents": 1000},
        ]
        entry = make_entry(store, org, lines=lines)
        self.assertEqual(entry["total_debits_cents"], 1000)

    def test_viewer_cannot_record_and_missing_entry_404s(self):
        store, _ = make_store()
        org = make_org(store)
        with self.assertRaises(PermissionDenied):
            make_entry(store, org, actor=VIEWER)
        with self.assertRaises(NotFoundError):
            store.get_ledger_entry(OPERATOR, "led-99")


if __name__ == "__main__":
    unittest.main()
