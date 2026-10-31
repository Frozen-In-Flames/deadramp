"""Core functions 7 & 8: alert subscriptions and alert records.

Subscriptions and alerts are records. The trigger-evaluation
engine and every delivery transport are Extended: this build
records alerts, it does not send them and it does not evaluate
triggers.
"""

import unittest

from energy.errors import NotFoundError, PermissionDenied, ValidationError

from energy_helpers import VIEWER, make_customer, make_store, ADMIN


class AlertTests(unittest.TestCase):
    def setUp(self):
        self.store, self.audit = make_store()
        self.customer = make_customer(self.store)

    def subscribe(self, kind="price_change", **kw):
        return self.store.create_subscription(ADMIN, self.customer["id"],
                                              kind, **kw)

    def test_subscription_created_active(self):
        sub = self.subscribe(threshold_cents_per_unit=300,
                             region="ERCOT-North", commodity="electricity")
        self.assertEqual(sub["id"], "sub-1")
        self.assertTrue(sub["active"])
        self.assertEqual(sub["threshold_cents_per_unit"], 300)
        self.assertEqual(sub["kind"], "price_change")

    def test_subscription_validation(self):
        with self.assertRaises(ValidationError):
            self.subscribe(kind="sms_everything")
        with self.assertRaises(ValidationError):
            self.subscribe(threshold_cents_per_unit=2.5)
        with self.assertRaises(NotFoundError):
            self.store.create_subscription(ADMIN, "cust-99", "price_change")

    def test_deactivate(self):
        sub = self.subscribe()
        done = self.store.deactivate_subscription(ADMIN, sub["id"])
        self.assertFalse(done["active"])
        with self.assertRaises(ValidationError):
            self.store.deactivate_subscription(ADMIN, sub["id"])
        active = self.store.list_subscriptions(ADMIN, active=True)
        self.assertEqual(active, [])
        self.assertEqual(len(self.store.list_subscriptions(ADMIN)), 1)

    def test_alert_recorded_not_delivered(self):
        sub = self.subscribe(kind="contract_change")
        alert = self.store.record_alert(ADMIN, self.customer["id"],
                                        "contract_change",
                                        "Supply contract terms changed",
                                        subscription_id=sub["id"])
        self.assertEqual(alert["id"], "alrt-1")
        self.assertEqual(alert["subscription_id"], sub["id"])
        self.assertNotIn("delivered", alert)
        self.assertNotIn("channel", alert)

    def test_alert_validation(self):
        other = self.store.create_customer(ADMIN, "CUST-0002", "other")
        sub = self.subscribe(kind="market_update")
        with self.assertRaises(ValidationError):
            self.store.record_alert(ADMIN, self.customer["id"], "weather",
                                    "subject")
        with self.assertRaises(ValidationError):
            self.store.record_alert(ADMIN, other["id"], "market_update",
                                    "subject", subscription_id=sub["id"])
        with self.assertRaises(NotFoundError):
            self.store.record_alert(ADMIN, self.customer["id"],
                                    "market_update", "subject",
                                    subscription_id="sub-99")
        listed = self.store.list_alerts(ADMIN, kind="market_update")
        self.assertEqual(listed, [])

    def test_roles(self):
        with self.assertRaises(PermissionDenied):
            self.store.create_subscription(VIEWER, self.customer["id"],
                                           "price_change")
        with self.assertRaises(PermissionDenied):
            self.store.record_alert(VIEWER, self.customer["id"],
                                    "price_change", "subject")


if __name__ == "__main__":
    unittest.main()
