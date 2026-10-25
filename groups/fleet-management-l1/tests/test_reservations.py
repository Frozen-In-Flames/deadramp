"""Reservation & assignment record tests.

Traces to: Core function 3 (Reservation & assignment records) --
lifecycle reserved -> checked_out -> returned, reserved -> cancelled;
illegal transitions rejected; and the implemented overlap rule: no
second active (reserved or checked_out) reservation for the same
vehicle, regardless of window.
"""

import unittest

from fleet_helpers import ADMIN, MANAGER, make_store
from fleet.errors import NotFoundError, ValidationError

START, END = "2026-11-01", "2026-11-03"


class TestReservations(unittest.TestCase):
    """Core 3: reservation shape, lifecycle, overlap rule."""

    def test_create_shape(self):
        """Core 3: a reservation record starts 'reserved' with a res- id."""
        store, vehicle, operator = make_store()
        res = store.create_reservation(vehicle["id"], operator["operator_ref"], START, END, MANAGER)
        self.assertEqual(res["id"], "res-1")
        self.assertEqual(res["status"], "reserved")
        self.assertEqual(res["vehicle_id"], vehicle["id"])
        self.assertEqual(res["operator_ref"], "OP-REF-001")

    def test_unknown_vehicle_not_found(self):
        """Core 3: reserving an unknown vehicle -> NotFoundError, nothing stored."""
        store, vehicle, operator = make_store()
        with self.assertRaises(NotFoundError):
            store.create_reservation("veh-999", "OP-X", START, END, ADMIN)
        self.assertEqual(store.list_reservations(actor=ADMIN), [])

    def test_end_must_follow_start(self):
        """Core 3 (SI-10): end <= start or unparseable dates -> ValidationError, no id consumed."""
        store, vehicle, operator = make_store()
        with self.assertRaises(ValidationError):
            store.create_reservation(vehicle["id"], "OP", END, START, ADMIN)
        with self.assertRaises(ValidationError):
            store.create_reservation(vehicle["id"], "OP", "not-a-date", END, ADMIN)
        res = store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        self.assertEqual(res["id"], "res-1")

    def test_happy_path_lifecycle(self):
        """Core 3 lifecycle: reserved -> checked_out -> returned, then the vehicle can be reserved again."""
        store, vehicle, operator = make_store()
        res = store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        res = store.set_reservation_status(res["id"], "checked_out", MANAGER)
        self.assertEqual(res["status"], "checked_out")
        res = store.set_reservation_status(res["id"], "returned", MANAGER)
        self.assertEqual(res["status"], "returned")
        res2 = store.create_reservation(vehicle["id"], "OP", "2026-11-10", "2026-11-11", ADMIN)
        self.assertEqual(res2["status"], "reserved")

    def test_cancel_path(self):
        """Core 3 lifecycle: reserved -> cancelled frees the vehicle for a new reservation."""
        store, vehicle, operator = make_store()
        res = store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        res = store.set_reservation_status(res["id"], "cancelled", ADMIN)
        self.assertEqual(res["status"], "cancelled")
        self.assertEqual(store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)["id"], "res-2")

    def test_illegal_transitions_rejected_state_unchanged(self):
        """Core 3 lifecycle gate: illegal, same-state, terminal and unknown transitions -> ValidationError, state unchanged."""
        store, vehicle, operator = make_store()
        res = store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        for bad in ("reserved", "returned", "bogus"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError):
                    store.set_reservation_status(res["id"], bad, ADMIN)
                self.assertEqual(store.get_reservation(res["id"])["status"], "reserved")
        store.set_reservation_status(res["id"], "cancelled", ADMIN)
        with self.assertRaises(ValidationError):
            store.set_reservation_status(res["id"], "checked_out", ADMIN)
        self.assertEqual(store.get_reservation(res["id"])["status"], "cancelled")

    def test_overlap_rule_no_second_active(self):
        """Core 3 overlap rule: a second reservation for a vehicle with an active (reserved or checked_out) reservation -> ValidationError, no id consumed."""
        store, vehicle, operator = make_store()
        other = store.create_vehicle("Other Van", "van", ADMIN)
        store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        with self.assertRaises(ValidationError):
            store.create_reservation(vehicle["id"], "OP2", "2027-01-01", "2027-01-02", ADMIN)
        # A different vehicle is unaffected, and gets the next id (no id was consumed above).
        self.assertEqual(store.create_reservation(other["id"], "OP", START, END, ADMIN)["id"], "res-2")
        # checked_out is still active for the overlap rule.
        store.set_reservation_status("res-1", "checked_out", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_reservation(vehicle["id"], "OP3", START, END, ADMIN)

    def test_list_filters(self):
        """Core 3: list_reservations filters by vehicle_id and status."""
        store, vehicle, operator = make_store()
        res = store.create_reservation(vehicle["id"], "OP", START, END, ADMIN)
        self.assertEqual(len(store.list_reservations(vehicle_id=vehicle["id"], actor=ADMIN)), 1)
        self.assertEqual(len(store.list_reservations(status="reserved", actor=ADMIN)), 1)
        self.assertEqual(store.list_reservations(status="returned", actor=ADMIN), [])


if __name__ == "__main__":
    unittest.main()
