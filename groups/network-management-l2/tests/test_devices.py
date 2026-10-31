"""Core functions 3 & 7: device inventory and derived device status.

The stored device record is pinned (exactly nine keys, no derived
key); freshness (fresh / stale / unknown) exists only on read views,
derived from telemetry against a 24-hour window.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import PermissionDenied, ValidationError

STORED_KEYS = {"id", "org_id", "network_id", "ref", "device_class",
               "model_ref", "state", "created_by", "created_utc"}


class TestDevices(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.network = H.make_network(self.store, self.org)

    def test_create_shape_is_pinned_and_starts_registered(self):
        device = H.make_device(self.store, self.org, self.network)
        self.assertTrue(device["id"].startswith("dev-"))
        self.assertEqual(device["state"], "registered")
        stored = self.store._devices[device["id"]]
        self.assertEqual(set(stored.keys()), STORED_KEYS)

    def test_read_view_adds_derived_keys_never_stored(self):
        device = H.make_device(self.store, self.org, self.network)
        view = self.store.get_device(H.MEMBER, device["id"])
        self.assertEqual(view["derived_status"], "unknown")
        self.assertIsNone(view["last_reading_utc"])
        stored = self.store._devices[device["id"]]
        self.assertNotIn("derived_status", stored)
        self.assertNotIn("last_reading_utc", stored)

    def test_derived_status_fresh_within_24h(self):
        device = H.make_device(self.store, self.org, self.network)
        H.make_telemetry(self.store, self.org, device)
        view = self.store.get_device(H.MEMBER, device["id"],
                                     as_of=H.AS_OF_FRESH)
        self.assertEqual(view["derived_status"], "fresh")
        self.assertEqual(view["last_reading_utc"], H.TELEMETRY_RECORDED_UTC)

    def test_derived_status_stale_after_24h(self):
        device = H.make_device(self.store, self.org, self.network)
        H.make_telemetry(self.store, self.org, device)
        view = self.store.get_device(H.MEMBER, device["id"],
                                     as_of=H.AS_OF_STALE)
        self.assertEqual(view["derived_status"], "stale")
        listed = self.store.list_devices(H.MEMBER, self.org["id"],
                                         as_of=H.AS_OF_STALE)
        self.assertEqual(listed[0]["derived_status"], "stale")

    def test_invalid_class_and_duplicate_ref_rejected(self):
        with self.assertRaises(ValidationError):
            H.make_device(self.store, self.org, self.network,
                          device_class="router")
        H.make_device(self.store, self.org, self.network)
        with self.assertRaises(ValidationError):
            H.make_device(self.store, self.org, self.network,
                          model_ref="MODEL-OTHER")

    def test_network_from_another_org_rejected(self):
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        other_network = H.make_network(self.store, other)
        with self.assertRaises(ValidationError):
            self.store.create_device(H.MEMBER, self.org["id"],
                                     other_network["id"], "DEV-X",
                                     "other", "MODEL-X")

    def test_retire_lifecycle(self):
        device = H.make_device(self.store, self.org, self.network)
        retired = self.store.retire_device(H.MEMBER, device["id"])
        self.assertEqual(retired["state"], "retired")
        with self.assertRaises(ValidationError):
            self.store.retire_device(H.MEMBER, device["id"])

    def test_outsider_cannot_read_device(self):
        device = H.make_device(self.store, self.org, self.network)
        with self.assertRaises(PermissionDenied):
            self.store.get_device(H.OUTSIDER, device["id"])


if __name__ == "__main__":
    unittest.main()
