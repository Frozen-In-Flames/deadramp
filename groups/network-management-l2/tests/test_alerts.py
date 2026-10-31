"""Core function 8: alert records -- kinds, linkage validation,
acknowledgement flow. Alerts are recorded, never delivered.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import ValidationError


class TestAlerts(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.network, self.device = H.make_estate(self.store, self.org)

    def test_create_shape_starts_unacknowledged(self):
        alert = H.make_alert(self.store, self.org,
                             network_id=self.network["id"],
                             device_id=self.device["id"])
        self.assertEqual(
            set(alert.keys()),
            {"id", "org_id", "network_id", "device_id", "kind",
             "message", "acknowledged_by", "acknowledged_utc",
             "created_by", "created_utc"})
        self.assertTrue(alert["id"].startswith("alr-"))
        self.assertIsNone(alert["acknowledged_by"])
        self.assertIsNone(alert["acknowledged_utc"])

    def test_invalid_kind_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_alert(self.store, self.org, kind="page_on_call")

    def test_cross_network_device_rejected(self):
        other_network = H.make_network(
            self.store, self.org, ref="NET-BR", label="Branch",
            site_ref="SITE-BR")
        with self.assertRaises(ValidationError):
            H.make_alert(self.store, self.org,
                         network_id=other_network["id"],
                         device_id=self.device["id"])

    def test_acknowledge_sets_fields_and_twice_is_an_error(self):
        alert = H.make_alert(self.store, self.org)
        acked = self.store.acknowledge_alert(H.MEMBER, alert["id"])
        self.assertEqual(acked["acknowledged_by"], "bob")
        self.assertIsNotNone(acked["acknowledged_utc"])
        with self.assertRaises(ValidationError):
            self.store.acknowledge_alert(H.STAFF, alert["id"])
        listed = self.store.list_alerts(H.MEMBER, self.org["id"])
        self.assertEqual(len(listed), 1)


if __name__ == "__main__":
    unittest.main()
