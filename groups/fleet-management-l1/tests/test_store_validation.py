"""Store validation tests.

Traces to: SI-10 (information input validation) and the contract rule
that malformed input raises ValidationError and changes nothing
(no id consumed), with permission checked before any state change.
"""

import unittest

from fleet_helpers import ADMIN, VIEWER, fresh_store, make_store
from fleet.errors import PermissionDenied, ValidationError


class TestStoreValidation(unittest.TestCase):
    """SI-10: validation leaves the store unchanged; permission precedes allocation."""

    def test_invalid_inputs_consume_no_ids_across_types(self):
        """SI-10: failed creates across types consume no sequential ids."""
        store, vehicle, operator = make_store()
        with self.assertRaises(ValidationError):
            store.create_vehicle("", "sedan", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_operator("", "license", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_reservation(vehicle["id"], "OP", "2026-11-03", "2026-11-01", ADMIN)
        with self.assertRaises(ValidationError):
            store.record_usage(vehicle["id"], -1, ADMIN)
        with self.assertRaises(ValidationError):
            store.create_maintenance(vehicle["id"], "maintenance", "not-a-date", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_charging_session("STN", "OP", ADMIN, watt_hours=1.5)
        self.assertEqual(store.create_vehicle("Second", "van", ADMIN)["id"], "veh-2")
        self.assertEqual(store.create_operator("OP-2", "license", ADMIN)["id"], "opr-2")
        self.assertEqual(store.create_reservation(vehicle["id"], "OP", "2026-11-01", "2026-11-02", ADMIN)["id"], "res-1")
        self.assertEqual(store.record_usage(vehicle["id"], 100, ADMIN)["id"], "use-1")
        self.assertEqual(store.create_maintenance(vehicle["id"], "inspection", "2026-12-01", ADMIN)["id"], "mnt-1")
        self.assertEqual(store.create_charging_session("STN", "OP", ADMIN)["id"], "chg-1")

    def test_permission_checked_before_validation_and_id(self):
        """AC-3/SI-10: a denied actor gets PermissionDenied even with malformed input, and nothing is allocated."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_vehicle("", "sedan", VIEWER)
        self.assertEqual(store.list_vehicles(ADMIN), [])
        self.assertEqual(store.create_vehicle("First", "sedan", ADMIN)["id"], "veh-1")

    def test_none_actor_write_denied(self):
        """AC-3: a write with no actor is PermissionDenied."""
        store = fresh_store()
        with self.assertRaises(PermissionDenied):
            store.create_vehicle("X", "sedan", None)

    def test_bad_types_rejected(self):
        """SI-10: non-string labels / wrong-typed fields -> ValidationError."""
        store, vehicle, operator = make_store()
        with self.assertRaises(ValidationError):
            store.create_vehicle(123, "sedan", ADMIN)
        with self.assertRaises(ValidationError):
            store.create_vehicle("Ok", 42, ADMIN)
        with self.assertRaises(ValidationError):
            store.record_usage(vehicle["id"], "1000", ADMIN)


if __name__ == "__main__":
    unittest.main()
