"""Check-in / check-out activity record tests.

Traces to: Core function 4 (Check-in / check-out activity records) --
the implemented design: an activity record DRIVES the reservation
lifecycle (check_out: reserved -> checked_out; check_in: checked_out
-> returned); a mismatched activity is rejected and records nothing.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, make_store
from fleet.errors import ValidationError


def _reserved(store, vehicle, operator):
    """Check-in helper: a fresh reserved reservation."""
    return store.create_reservation(vehicle["id"], operator["operator_ref"],
                                    "2026-11-01", "2026-11-03", ADMIN)


class TestCheckins(unittest.TestCase):
    """Core 4: check-in/check-out records drive the reservation lifecycle."""

    def test_check_out_and_in_drive_lifecycle(self):
        """Core 4: check_out moves reserved -> checked_out; check_in moves checked_out -> returned; records carry chk- ids."""
        store, vehicle, operator = make_store()
        res = _reserved(store, vehicle, operator)
        out = store.record_checkin(res["id"], "check_out", 12000, MANAGER)
        self.assertEqual(out["id"], "chk-1")
        self.assertEqual(set(out), {"id", "reservation_id", "kind", "odometer",
                                    "recorded_utc", "created_by"})
        self.assertEqual(store.get_reservation(res["id"])["status"], "checked_out")
        back = store.record_checkin(res["id"], "check_in", 12150, MANAGER)
        self.assertEqual(back["id"], "chk-2")
        self.assertEqual(store.get_reservation(res["id"])["status"], "returned")
        self.assertEqual(len(store.list_checkins(reservation_id=res["id"], actor=ADMIN)), 2)

    def test_check_in_before_out_rejected(self):
        """Core 4: check_in on a merely reserved reservation -> ValidationError, nothing recorded, no id consumed."""
        store, vehicle, operator = make_store()
        res = _reserved(store, vehicle, operator)
        with self.assertRaises(ValidationError):
            store.record_checkin(res["id"], "check_in", 12000, ADMIN)
        self.assertEqual(store.list_checkins(actor=ADMIN), [])
        self.assertEqual(store.get_reservation(res["id"])["status"], "reserved")
        self.assertEqual(store.record_checkin(res["id"], "check_out", 12000, ADMIN)["id"], "chk-1")

    def test_double_check_out_rejected(self):
        """Core 4: a second check_out on a checked_out reservation -> ValidationError."""
        store, vehicle, operator = make_store()
        res = _reserved(store, vehicle, operator)
        store.record_checkin(res["id"], "check_out", 100, ADMIN)
        with self.assertRaises(ValidationError):
            store.record_checkin(res["id"], "check_out", 101, ADMIN)

    def test_bad_kind_and_odometer_rejected(self):
        """Core 4 (SI-10): unknown kind, negative / non-integer odometer -> ValidationError."""
        store, vehicle, operator = make_store()
        res = _reserved(store, vehicle, operator)
        with self.assertRaises(ValidationError):
            store.record_checkin(res["id"], "peek", 100, ADMIN)
        for bad in (-1, 12.5, "100", True, None):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    store.record_checkin(res["id"], "check_out", bad, ADMIN)
        self.assertEqual(store.list_checkins(actor=ADMIN), [])


if __name__ == "__main__":
    unittest.main()
