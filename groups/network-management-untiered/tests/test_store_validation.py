"""Cross-cutting: SI-10 atomicity, telemetry value boundary,
no-score shapes (recursive key scan).
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import ValidationError

FORBIDDEN_KEY_PARTS = ("score", "rating", "health", "optimization")


def _all_keys(obj):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield str(key)
            yield from _all_keys(value)
    elif isinstance(obj, (list, tuple)):
        for value in obj:
            yield from _all_keys(value)


class TestAtomicity(unittest.TestCase):
    def test_failed_operation_consumes_no_id(self):
        store, org = H.make_store()
        network = H.make_network(store, org)
        with self.assertRaises(ValidationError):
            store.create_device(H.MEMBER, org["id"], network["id"],
                                "DEV-BAD", "router", "MODEL-X")
        device = H.make_device(store, org, network)
        self.assertEqual(device["id"], "dev-1")
        with self.assertRaises(ValidationError):
            store.record_telemetry(H.MEMBER, org["id"], device["id"],
                                   "throughput", 1.5, "mbps",
                                   H.TELEMETRY_RECORDED_UTC)
        record = H.make_telemetry(store, org, device)
        self.assertEqual(record["id"], "tel-1")
        with self.assertRaises(ValidationError):
            store.create_change(H.MEMBER, org["id"], network["id"],
                                "restart", "Nope")
        change = H.make_change(store, org, network)
        self.assertEqual(change["id"], "chg-1")

    def test_failed_operation_changes_nothing(self):
        store, org = H.make_store()
        network, device = H.make_estate(store, org)
        before = store.organization_summary(H.MEMBER, org["id"])
        with self.assertRaises(ValidationError):
            store.record_telemetry(H.MEMBER, org["id"], device["id"],
                                   "throughput", "100", "mbps",
                                   H.TELEMETRY_RECORDED_UTC)
        after = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(before, after)


class TestNoComputedScores(unittest.TestCase):
    def test_no_score_field_on_any_view(self):
        """Nothing in the build scores, rates, or optimizes: no
        returned view -- recursively -- carries such a key."""
        store, org = H.make_store()
        network, device = H.make_estate(store, org)
        record = H.make_telemetry(store, org, device)
        change = H.make_change(store, org, network,
                               device_id=device["id"])
        automation = H.make_automation(store, org)
        alert = H.make_alert(store, org, network_id=network["id"],
                             device_id=device["id"])
        views = [
            org, network, device, record, change, automation, alert,
            store.get_device(H.MEMBER, device["id"], as_of=H.AS_OF_FRESH),
            store.list_devices(H.MEMBER, org["id"]),
            store.search(H.MEMBER, "hq"),
            store.organization_summary(H.MEMBER, org["id"]),
        ]
        for view in views:
            for key in _all_keys(view):
                lowered = key.lower()
                for forbidden in FORBIDDEN_KEY_PARTS:
                    self.assertNotIn(forbidden, lowered,
                                     "%s in key %r of %r"
                                     % (forbidden, key, view))


if __name__ == "__main__":
    unittest.main()
