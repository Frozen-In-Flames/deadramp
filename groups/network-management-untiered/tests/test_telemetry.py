"""Core function 6: telemetry records -- integer values, ISO-8601
timestamps, org-scoped devices (SI-10). Records only; nothing is
collected or polled.
"""

import unittest

import netmgmt_helpers as H
from netmgmt.errors import ValidationError


class TestTelemetry(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.network, self.device = H.make_estate(self.store, self.org)

    def test_record_shape_is_pinned(self):
        record = H.make_telemetry(self.store, self.org, self.device)
        self.assertEqual(
            set(record.keys()),
            {"id", "org_id", "device_id", "metric", "value", "unit",
             "recorded_utc", "created_by", "created_utc"})
        self.assertTrue(record["id"].startswith("tel-"))
        self.assertEqual(record["value"], 100)

    def test_non_integer_values_rejected(self):
        for bad in (True, False, 1.5, 100.0, "100", None):
            with self.assertRaises(ValidationError):
                H.make_telemetry(self.store, self.org, self.device,
                                 value=bad)
        self.assertEqual(
            self.store.list_telemetry(H.MEMBER, self.device["id"]), [])

    def test_trailing_z_timestamp_accepted(self):
        record = H.make_telemetry(self.store, self.org, self.device,
                                  recorded_utc="2026-06-01T08:00:00Z")
        self.assertEqual(record["recorded_utc"], "2026-06-01T08:00:00Z")
        view = self.store.get_device(H.MEMBER, self.device["id"],
                                     as_of=H.AS_OF_FRESH)
        self.assertEqual(view["derived_status"], "fresh")

    def test_unparseable_timestamp_rejected(self):
        for bad in ("not-a-date", "2026-13-01T00:00:00+00:00", "", None, 42):
            with self.assertRaises(ValidationError):
                H.make_telemetry(self.store, self.org, self.device,
                                 recorded_utc=bad)

    def test_device_from_another_org_rejected(self):
        other = H.make_org(self.store, ref="AGENCY-2", label="Agency Two")
        with self.assertRaises(ValidationError):
            self.store.record_telemetry(
                H.MEMBER, other["id"], self.device["id"], "throughput",
                1, "mbps", H.TELEMETRY_RECORDED_UTC)

    def test_list_telemetry_for_device(self):
        H.make_telemetry(self.store, self.org, self.device)
        H.make_telemetry(self.store, self.org, self.device,
                         metric="latency", value=12, unit="ms",
                         recorded_utc="2026-06-01T09:00:00+00:00")
        records = self.store.list_telemetry(H.MEMBER, self.device["id"])
        self.assertEqual(len(records), 2)
        view = self.store.get_device(H.MEMBER, self.device["id"],
                                     as_of=H.AS_OF_FRESH)
        self.assertEqual(view["last_reading_utc"],
                         "2026-06-01T09:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
