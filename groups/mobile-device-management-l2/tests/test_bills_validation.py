"""Core function 6: bill records & validation runs (SI-10)."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestBills(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)

    def test_period_must_be_yyyy_mm(self):
        for bad in ("2026-13", "2026-00", "June 2026", "2026/06", 202606):
            with self.assertRaises(ValidationError):
                H.make_bill(self.store, self.org, self.contract, period=bad)

    def test_bill_shape(self):
        bill = H.make_bill(self.store, self.org, self.contract)
        self.assertEqual(bill["stated_cents"], 50_000)
        self.assertEqual(bill["period"], "2026-06")


class TestValidationRuns(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.contract = H.make_contract(self.store, self.org)
        # Billable inventory: 50,000 + 25,000 + 10,000 = 85,000.
        H.make_inventory(self.store, self.org)
        self.mob = H.make_inventory(
            self.store, self.org, ref="SVC-200", service_kind="mobility",
            label="Field lines", plan_ref="PLAN-MOB-1",
            monthly_recurring_cents=25_000)
        H.make_inventory(
            self.store, self.org, ref="SVC-300", service_kind="other",
            label="Future service", plan_ref="PLAN-FUT-1",
            monthly_recurring_cents=10_000)

    def test_match_when_stated_equals_expected(self):
        bill = H.make_bill(self.store, self.org, self.contract,
                           stated_cents=85_000)
        run = self.store.validate_bill(H.MEMBER, bill["id"])
        self.assertEqual(run["expected_cents"], 85_000)
        self.assertEqual(run["variance_cents"], 0)
        self.assertEqual(run["result"], "match")

    def test_variance_is_recorded_arithmetic(self):
        bill = H.make_bill(self.store, self.org, self.contract,
                           stated_cents=86_500)
        run = self.store.validate_bill(H.MEMBER, bill["id"])
        self.assertEqual(run["variance_cents"], 1_500)
        self.assertEqual(run["result"], "variance")

    def test_disconnected_items_leave_the_expected_total(self):
        """The check's stated rule: disconnected items do not bill."""
        order = self.store.create_order(
            H.MEMBER, self.org["id"], "disconnect", "Drop field lines",
            inventory_id=self.mob["id"])
        self.store.decide_order(H.STAFF, order["id"], True)
        self.store.fulfill_order(H.MEMBER, order["id"])
        bill = H.make_bill(self.store, self.org, self.contract,
                           stated_cents=60_000)
        run = self.store.validate_bill(H.MEMBER, bill["id"])
        self.assertEqual(run["expected_cents"], 60_000)
        self.assertEqual(run["result"], "match")

    def test_validation_modifies_nothing(self):
        bill = H.make_bill(self.store, self.org, self.contract,
                           stated_cents=86_500)
        self.store.validate_bill(H.MEMBER, bill["id"])
        after = self.store.get_bill(H.MEMBER, bill["id"])
        self.assertEqual(after, bill)
        runs = self.store.list_validations(H.MEMBER, bill["id"])
        self.assertEqual(len(runs), 1)


if __name__ == "__main__":
    unittest.main()
