"""Core functions 9 (chargebacks) and 10 (alert records)."""

import unittest

import mdm_helpers as H
from mdm.errors import ValidationError


class TestChargebacks(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.budget = H.make_budget(self.store, self.org)

    def test_chargeback_record(self):
        chargeback = self.store.create_chargeback(
            H.MEMBER, self.budget["id"], "UNIT-FIELD-OPS", 12_500,
            note="June mobility share")
        self.assertEqual(chargeback["unit_ref"], "UNIT-FIELD-OPS")
        listed = self.store.list_chargebacks(H.MEMBER, self.budget["id"])
        self.assertEqual(len(listed), 1)

    def test_chargeback_validation(self):
        for amount in (0, -1, 12.5, "125"):
            with self.assertRaises(ValidationError):
                self.store.create_chargeback(
                    H.MEMBER, self.budget["id"], "UNIT-X", amount)
        with self.assertRaises(ValidationError):
            self.store.create_chargeback(
                H.MEMBER, self.budget["id"], "  ", 100)


class TestAlerts(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.budget = H.make_budget(self.store, self.org)

    def test_alert_record_and_acknowledgement(self):
        alert = self.store.create_alert(
            H.MEMBER, self.org["id"], "budget_threshold",
            "Spent plus obligated exceeds 80% of the June budget",
            budget_id=self.budget["id"])
        self.assertIsNone(alert["acknowledged_by"])
        acked = self.store.acknowledge_alert(H.STAFF, alert["id"])
        self.assertEqual(acked["acknowledged_by"], "erin")
        with self.assertRaises(ValidationError):
            self.store.acknowledge_alert(H.STAFF, alert["id"])

    def test_alert_kinds_validated(self):
        with self.assertRaises(ValidationError):
            self.store.create_alert(
                H.MEMBER, self.org["id"], "emergency", "Nope")
        for kind in ("budget_threshold", "budget_projection", "general"):
            alert = self.store.create_alert(
                H.MEMBER, self.org["id"], kind, "Note")
            self.assertEqual(alert["kind"], kind)


if __name__ == "__main__":
    unittest.main()
