"""Charging session record tests.

Traces to: Core function 7 (Charging session records) -- opaque
station/operator references, open until closed, and energy recorded
as INTEGER watt-hours (``watt_hours``), never a float.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, make_store
from fleet.errors import NotFoundError, ValidationError


class TestChargingSessions(unittest.TestCase):
    """Core 7: charging session create/close with integer watt-hours."""

    def test_create_shape_open_session(self):
        """Core 7: a new session is open (ended_utc None), carries chg- id and integer watt_hours (default 0)."""
        store, vehicle, operator = make_store()
        s = store.create_charging_session("STN-REF-1", operator["operator_ref"], MANAGER)
        self.assertEqual(s["id"], "chg-1")
        self.assertEqual(set(s), {"id", "station_ref", "operator_ref", "started_utc",
                                  "ended_utc", "watt_hours", "created_by"})
        self.assertIsNone(s["ended_utc"])
        self.assertEqual(s["watt_hours"], 0)
        self.assertIsInstance(s["watt_hours"], int)

    def test_close_records_end_and_energy(self):
        """Core 7: closing sets ended_utc and the final integer watt_hours; the closed record is returned by get/list."""
        store, vehicle, operator = make_store()
        s = store.create_charging_session("STN-1", "OP-1", ADMIN, started_utc="2026-11-01T08:00:00+00:00")
        closed = store.close_charging_session(s["id"], ADMIN,
                                              ended_utc="2026-11-01T09:30:00+00:00", watt_hours=22500)
        self.assertEqual(closed["ended_utc"], "2026-11-01T09:30:00+00:00")
        self.assertEqual(closed["watt_hours"], 22500)
        self.assertEqual(store.get_charging_session(s["id"], ADMIN)["watt_hours"], 22500)
        self.assertEqual(len(store.list_charging_sessions(ADMIN)), 1)

    def test_close_twice_rejected(self):
        """Core 7: closing an already-closed session -> ValidationError."""
        store, vehicle, operator = make_store()
        s = store.create_charging_session("STN-1", "OP-1", ADMIN)
        store.close_charging_session(s["id"], ADMIN)
        with self.assertRaises(ValidationError):
            store.close_charging_session(s["id"], ADMIN)

    def test_watt_hours_must_be_non_negative_int(self):
        """Core 7 (SI-10): float / negative / string watt_hours -> ValidationError on create and close; unknown session -> NotFoundError."""
        store, vehicle, operator = make_store()
        for bad in (1.5, -100, "22500", True):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    store.create_charging_session("STN-1", "OP-1", ADMIN, watt_hours=bad)
        s = store.create_charging_session("STN-1", "OP-1", ADMIN, watt_hours=100)
        self.assertEqual(s["id"], "chg-1")
        with self.assertRaises(ValidationError):
            store.close_charging_session(s["id"], ADMIN, watt_hours=-1)
        with self.assertRaises(NotFoundError):
            store.close_charging_session("chg-999", ADMIN)

    def test_empty_refs_rejected(self):
        """Core 7 (SI-10): empty station_ref / operator_ref -> ValidationError."""
        store, vehicle, operator = make_store()
        with self.assertRaises(ValidationError):
            store.create_charging_session("", "OP-1", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_charging_session("STN-1", "", ADMIN)
        self.assertEqual(store.list_charging_sessions(ADMIN), [])


if __name__ == "__main__":
    unittest.main()
