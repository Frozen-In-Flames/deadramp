"""Search and reporting tests.

Traces to: Core function 9 (Search over registry metadata) and Core
function 8 (Reporting -- counts per record set + per-vehicle usage
summary; registry reporting only, no analytics engine).
"""

import unittest

from fleet_helpers import ADMIN, VIEWER, make_store
from fleet.errors import ValidationError


def _populated():
    """Search/report helper: a store with one of every record type."""
    store, vehicle, operator = make_store()
    res = store.create_reservation(vehicle["id"], operator["operator_ref"],
                                   "2026-11-01", "2026-11-03", ADMIN)
    store.record_checkin(res["id"], "check_out", 12000, ADMIN)
    store.record_usage(vehicle["id"], 12000, ADMIN)
    store.create_maintenance(vehicle["id"], "inspection", "2026-12-01", ADMIN)
    session = store.create_charging_session("STN-ALPHA", operator["operator_ref"], ADMIN)
    store.close_charging_session(session["id"], ADMIN, watt_hours=22500)
    return store, vehicle, operator, res


class TestSearch(unittest.TestCase):
    """Core 9: substring search across the registry families."""

    def test_hits_across_families(self):
        """Core 9: search hits vehicles, operators, reservations, maintenance and charging sessions, case-insensitively."""
        store, vehicle, operator, res = _populated()
        found = store.search("pool", VIEWER)
        self.assertEqual(len(found["vehicles"]), 1)
        found = store.search("OP-REF", VIEWER)
        self.assertEqual(len(found["operators"]), 1)
        self.assertEqual(len(found["reservations"]), 1)
        self.assertEqual(len(found["charging_sessions"]), 1)
        found = store.search("inspection", VIEWER)
        self.assertEqual(len(found["maintenance"]), 1)
        found = store.search("stn-alpha", VIEWER)
        self.assertEqual(len(found["charging_sessions"]), 1)

    def test_no_hit_empty_lists(self):
        """Core 9: a query with no matches returns empty lists for every family."""
        store, vehicle, operator, res = _populated()
        found = store.search("zzz-no-match", VIEWER)
        self.assertTrue(all(found[k] == [] for k in
                            ("vehicles", "operators", "reservations", "maintenance", "charging_sessions")))

    def test_empty_query_rejected(self):
        """Core 9 (SI-10): empty / blank query -> ValidationError; the search action is required."""
        store, vehicle, operator, res = _populated()
        with self.assertRaises(ValidationError):
            store.search("", ADMIN)
        with self.assertRaises(ValidationError):
            store.search("   ", ADMIN)


class TestReporting(unittest.TestCase):
    """Core 8: summary report counts and per-vehicle usage summary."""

    def test_summary_counts_and_vehicle_usage(self):
        """Core 8: counts per record set, aggregate integer watt-hours, and per-vehicle latest odometer + record counts."""
        store, vehicle, operator, res = _populated()
        report = store.summary_report(VIEWER)
        self.assertEqual(report["counts"], {"vehicles": 1, "operators": 1, "reservations": 1,
                                            "checkins": 1, "usage": 1, "maintenance": 1,
                                            "charging_sessions": 1})
        self.assertEqual(report["total_watt_hours"], 22500)
        self.assertEqual(len(report["vehicles"]), 1)
        entry = report["vehicles"][0]
        self.assertEqual(entry["vehicle_id"], vehicle["id"])
        self.assertEqual(entry["latest_odometer"], 12000)
        self.assertEqual(entry["usage_records"], 1)
        self.assertEqual(entry["reservations"], 1)
        self.assertEqual(entry["checkins"], 1)
        self.assertEqual(entry["maintenance_records"], 1)

    def test_summary_empty_store(self):
        """Core 8: an empty store reports zero counts, zero energy, and no vehicle entries."""
        from fleet_helpers import fresh_store
        report = fresh_store().summary_report(ADMIN)
        self.assertTrue(all(v == 0 for v in report["counts"].values()))
        self.assertEqual(report["total_watt_hours"], 0)
        self.assertEqual(report["vehicles"], [])


if __name__ == "__main__":
    unittest.main()
