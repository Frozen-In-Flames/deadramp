import unittest

from travel.errors import ValidationError

from travel_helpers import (MEMBER, make_approved_authorization,
                            make_approved_report, make_report_with_items,
                            make_store, make_traveler)


class TestVouchers(unittest.TestCase):
    """The signature invariant: cumulative vouchers against an expense
    report never exceed the report's total (150,000 cents here)."""

    def setUp(self):
        self.store, self.org = make_store()
        self.traveler = make_traveler(self.store, self.org)
        self.auth = make_approved_authorization(self.store, self.org,
                                                self.traveler)
        self.report = make_approved_report(self.store, self.auth)

    def test_partial_voucher(self):
        voucher = self.store.record_voucher(MEMBER, self.report["id"], 50_000)
        self.assertEqual(voucher["amount_cents"], 50_000)
        view = self.store.get_expense_report(MEMBER, self.report["id"])
        self.assertEqual(view["reimbursed_cents"], 50_000)
        self.assertEqual(view["remaining_cents"], 100_000)

    def test_vouchers_up_to_exact_total(self):
        self.store.record_voucher(MEMBER, self.report["id"], 90_000)
        self.store.record_voucher(MEMBER, self.report["id"], 60_000)
        view = self.store.get_expense_report(MEMBER, self.report["id"])
        self.assertEqual(view["reimbursed_cents"], 150_000)
        self.assertEqual(view["remaining_cents"], 0)

    def test_voucher_one_cent_over_total_rejected(self):
        self.store.record_voucher(MEMBER, self.report["id"], 150_000)
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, self.report["id"], 1)

    def test_single_voucher_over_total_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, self.report["id"], 150_001)

    def test_rejected_voucher_changes_nothing(self):
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, self.report["id"], 150_001)
        self.assertEqual(self.store.list_vouchers(MEMBER, self.report["id"]),
                         [])

    def test_float_voucher_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, self.report["id"], 100.0)

    def test_zero_voucher_rejected(self):
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, self.report["id"], 0)

    def test_voucher_requires_approved_report(self):
        draft = make_report_with_items(self.store, self.auth)
        with self.assertRaises(ValidationError):
            self.store.record_voucher(MEMBER, draft["id"], 100)


if __name__ == "__main__":
    unittest.main()
