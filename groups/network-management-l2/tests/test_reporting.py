"""Core function 9: registry search & organization summary
(literal substring search; counts only, never scores).
"""

import unittest

import netmgmt_helpers as H


class TestSearch(unittest.TestCase):
    def setUp(self):
        self.store, self.org = H.make_store()
        self.network, self.device = H.make_estate(self.store, self.org)
        self.change = H.make_change(self.store, self.org, self.network)
        H.make_alert(self.store, self.org)

    def test_search_finds_networks_devices_changes_alerts(self):
        hits = self.store.search(H.MEMBER, "net-hq")
        self.assertEqual(len(hits["networks"]), 1)
        hits = self.store.search(H.MEMBER, "site-hq")
        self.assertEqual(len(hits["networks"]), 1)
        hits = self.store.search(H.MEMBER, "DEV-SW")
        self.assertEqual(len(hits["devices"]), 1)
        hits = self.store.search(H.MEMBER, "model-sw-1")
        self.assertEqual(len(hits["devices"]), 1)
        hits = self.store.search(H.MEMBER, "tune hq policy")
        self.assertEqual(len(hits["changes"]), 1)
        hits = self.store.search(H.MEMBER, "review hq network")
        self.assertEqual(len(hits["alerts"]), 1)

    def test_outsider_searches_see_nothing(self):
        hits = self.store.search(H.OUTSIDER, "hq")
        for key in ("networks", "devices", "changes", "alerts"):
            self.assertEqual(hits[key], [], key)

    def test_empty_query_returns_no_records(self):
        hits = self.store.search(H.MEMBER, "")
        self.assertEqual(
            hits, {"networks": [], "devices": [], "changes": [],
                   "alerts": []})


class TestSummary(unittest.TestCase):
    def test_summary_counts(self):
        store, org = H.make_store()
        network, device = H.make_estate(store, org)
        H.make_device(store, org, network, ref="DEV-AP-1",
                      device_class="wireless", model_ref="MODEL-AP-1")
        H.make_telemetry(store, org, device)
        change = H.make_change(store, org, network)
        store.decide_change(H.STAFF, change["id"], True)
        H.make_automation(store, org)
        alert = H.make_alert(store, org)
        H.make_alert(store, org, kind="device_stale",
                     message="Second alert")
        store.acknowledge_alert(H.MEMBER, alert["id"])
        summary = store.organization_summary(H.MEMBER, org["id"])
        self.assertEqual(summary["networks"], 1)
        self.assertEqual(summary["devices"], 2)
        self.assertEqual(summary["devices_by_class"],
                         {"switching": 1, "wireless": 1,
                          "security_sdwan": 0, "other": 0})
        self.assertEqual(summary["devices_by_state"],
                         {"registered": 2, "retired": 0})
        # Derived at summary time (as_of = now): the June 2026
        # reading is long past the 24-hour window, and the second
        # device has no reading at all.
        self.assertEqual(summary["devices_by_derived_status"],
                         {"fresh": 0, "stale": 1, "unknown": 1})
        self.assertEqual(summary["telemetry_records"], 1)
        self.assertEqual(summary["changes"], 1)
        self.assertEqual(summary["changes_by_status"]["approved"], 1)
        self.assertEqual(summary["automations"], 1)
        self.assertEqual(summary["alerts"], 2)
        self.assertEqual(summary["alerts_unacknowledged"], 1)


if __name__ == "__main__":
    unittest.main()
